"""
Smoke tests for the recommendation pipeline.

Run from backend/:  pytest -q

They use a temporary SQLite DB, a fake (deterministic) embedding model and a
fake external API, so they run offline in ~1s and don't download anything.
"""
import hashlib
import os
import sys
import tempfile

import numpy as np
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

_tmpdir = tempfile.mkdtemp()
os.environ["SQLITE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from schemas import ExternalSearchResult  # noqa: E402
from services.embedding import embedding_service  # noqa: E402
from services.external_api import external_api_service  # noqa: E402
from services.recommender import normalize_categories, recommender_service  # noqa: E402

DIM = 384

# ── Fakes ──────────────────────────────────────────────────────────────────────

_TOPICS = {
    "fantasia": 0, "fantasy": 0, "dragões": 0, "magia": 0, "dragons": 0,
    "suspense": 1, "thriller": 1, "crime": 1, "assassinato": 1,
    "ciência": 2, "science": 2, "física": 2, "cosmos": 2,
}


def fake_embed(text: str):
    """Deterministic embedding: a topic direction + a small text-specific hash component."""
    vec = np.zeros(DIM, dtype=np.float32)
    lowered = text.lower()
    for word, axis in _TOPICS.items():
        if word in lowered:
            vec[axis] += 1.0
    h = hashlib.sha256(text.encode()).digest()
    for i, b in enumerate(h[:16]):
        vec[10 + i] += (b / 255.0 - 0.5) * 0.2
    if not vec.any():
        vec[5] = 1.0
    return (vec / np.linalg.norm(vec)).tolist()


class FakeModel:
    def encode(self, texts, normalize_embeddings=True, batch_size=32):
        if isinstance(texts, str):
            return np.asarray(fake_embed(texts), dtype=np.float32)
        return np.asarray([fake_embed(t) for t in texts], dtype=np.float32)

    def get_sentence_embedding_dimension(self):
        return DIM


CATALOG = [
    ExternalSearchResult(external_id="g1", source="google_books", title="A Torre dos Dragões",
                         author="A. Fantasia", description="Magia e dragões numa saga de fantasia.",
                         categories=["Fiction / Fantasy / Epic"]),
    ExternalSearchResult(external_id="g2", source="google_books", title="Reinos de Magia",
                         author="B. Fantasia", description="Fantasia épica com magia antiga.",
                         categories=["Fantasy fiction"]),
    ExternalSearchResult(external_id="/works/OL1W", source="open_library", title="Noite do Assassinato",
                         author="C. Crime", description="Um thriller de suspense e crime.",
                         categories=["Thrillers", "Crime"]),
    ExternalSearchResult(external_id="g4", source="google_books", title="O Cosmos Explicado",
                         author="D. Ciência", description="Física e ciência para todos.",
                         categories=["Science"]),
]


async def fake_search(query, source="all", field=None):
    q = query.lower()
    if field == "author":
        return [r for r in CATALOG if r.author and q in r.author.lower()]
    return [r for r in CATALOG if q in (r.title + " " + (r.description or "")).lower()] or CATALOG


@pytest.fixture(scope="module")
def client():
    embedding_service.model = FakeModel()
    embedding_service.dim = DIM
    embedding_service.load_model = lambda: None
    external_api_service.search = fake_search
    with TestClient(main.app) as c:
        yield c


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_normalize_categories_bridges_sources_and_languages():
    assert normalize_categories(["Fiction / Thrillers / Suspense"]) == {"ficcao", "suspense"}
    assert normalize_categories(["Ficção Científica"]) == {"ficcao cientifica"}
    assert normalize_categories(["Science Fiction"]) == {"ficcao cientifica"}
    assert normalize_categories(["General"]) == set()


def test_no_history_gives_no_recommendations(client):
    assert client.get("/api/recommendations").json() == []


def test_recommendations_come_from_catalog_and_rank_by_taste(client):
    # User reads fantasy and loves it
    r = client.post("/api/books", json={
        "title": "Crônicas de Magia", "author": "Z. Autor",
        "description": "Fantasia com dragões e magia.", "categories": ["Fantasia"],
        "status": "read", "rating": 5,
    })
    assert r.status_code == 201, r.text

    # Catalog is still empty -> nothing to recommend yet
    assert client.get("/api/recommendations").json() == []

    # External searches fill the catalog
    r = client.get("/api/external/search", params={"q": "magia"})
    assert r.status_code == 200 and recommender_service.size == 2
    r = client.get("/api/external/search", params={"q": "livros"})  # fake returns everything
    assert r.status_code == 200
    assert recommender_service.size == len(CATALOG)

    recs = client.get("/api/recommendations", params={"limit": 10}).json()
    titles = [x["title"] for x in recs]
    assert len(recs) == len(CATALOG)
    assert titles[0] in ("A Torre dos Dragões", "Reinos de Magia")
    assert titles[-1] != titles[0]
    assert recs[0]["score"] >= recs[-1]["score"]
    assert recs[0]["category_score"] > 0  # "Fantasia" ↔ "Fiction / Fantasy / Epic"
    assert "Combina" in recs[0]["reason"]
    assert all("external_id" in x and "source" in x for x in recs)


def test_genre_filter_uses_canonical_tokens(client):
    recs = client.get("/api/recommendations", params={"genre": "suspense"}).json()
    assert [x["title"] for x in recs] == ["Noite do Assassinato"]
    recs = client.get("/api/recommendations", params={"genre": "thriller"}).json()
    assert [x["title"] for x in recs] == ["Noite do Assassinato"]


def test_import_removes_book_from_candidates(client):
    before = recommender_service.size
    r = client.post("/api/external/import/%2Fworks%2FOL1W",
                    params={"source": "open_library", "status": "wishlist"})
    assert r.status_code == 201, r.text
    assert r.json()["book"]["external_id"] == "/works/OL1W"
    assert recommender_service.size == before - 1

    titles = [x["title"] for x in client.get("/api/recommendations").json()]
    assert "Noite do Assassinato" not in titles

    # Importing again does not duplicate
    r2 = client.post("/api/external/import/%2Fworks%2FOL1W", params={"source": "open_library"})
    assert r2.status_code == 201 and r2.json()["id"] == r.json()["id"]


def test_editing_a_library_book_does_not_touch_the_index(client):
    before = recommender_service.size
    ub = client.get("/api/books").json()[0]
    r = client.patch(f"/api/books/{ub['id']}", json={"description": "Nova descrição"})
    assert r.status_code == 200
    assert recommender_service.size == before


def test_discover_grows_catalog_from_top_interests(client):
    r = client.post("/api/recommendations/discover")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["queries"]  # built from the user's authors/categories
    assert body["catalog_size"] == recommender_service.size


def test_rating_validation(client):
    ub = client.get("/api/books").json()[0]
    assert client.patch(f"/api/books/{ub['id']}", json={"rating": 9}).status_code == 422
    assert client.patch(f"/api/books/{ub['id']}", json={"status": "lido"}).status_code == 422
