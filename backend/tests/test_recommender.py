"""
Smoke tests for the recommendation pipeline.

Run from backend/:  pytest -q

They use a temporary SQLite DB, a fake (deterministic) embedding model and a
fake external API, so they run offline in ~1s and don't download anything.
"""
from types import SimpleNamespace

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


# ── Unit tests: RecommenderService internals (no DB, no HTTP client) ────────────
# These isolate the signed-rating logic added to fix "1-star still attracts".

def _axis_vector(axis, dim=DIM):
    v = np.zeros(dim, dtype=np.float32)
    v[axis] = 1.0
    return v.tolist()


def _fake_book(embedding, categories=None, author="Author"):
    return SimpleNamespace(embedding=embedding, categories=categories or [], author=author)


def _fake_user_book(rating, embedding, categories=None, author="Author"):
    return SimpleNamespace(rating=rating, book=_fake_book(embedding, categories, author))


def test_profile_empty_history_returns_none():
    assert recommender_service.compute_user_profile([]) is None


def test_profile_ignores_books_without_usable_embedding():
    ubs = [
        SimpleNamespace(rating=5, book=None),                    # no book
        SimpleNamespace(rating=5, book=_fake_book(None)),         # no embedding
        SimpleNamespace(rating=5, book=_fake_book([0.1] * 10)),   # wrong dimension
    ]
    assert recommender_service.compute_user_profile(ubs) is None


def test_profile_unrated_book_still_contributes_positively():
    profile = recommender_service.compute_user_profile([_fake_user_book(None, _axis_vector(0))])
    assert profile is not None
    assert profile[0] == pytest.approx(1.0, abs=1e-5)


def test_profile_five_star_outweighs_one_star_on_orthogonal_axes():
    ubs = [
        _fake_user_book(5, _axis_vector(0)),  # weight +2.5 (loved)
        _fake_user_book(1, _axis_vector(1)),  # weight -1.5 (hated)
    ]
    profile = recommender_service.compute_user_profile(ubs)
    assert profile[0] > 0                  # attracted toward the loved topic
    assert profile[1] < 0                  # repelled from the hated topic
    assert profile[0] > abs(profile[1])    # 2.5 > 1.5, loved signal dominates


def test_profile_opposite_signals_of_equal_weight_cancel_to_none():
    e = _axis_vector(0)
    opposite = (-np.asarray(e)).tolist()
    ubs = [
        _fake_user_book(3, e),         # weight +0.5
        _fake_user_book(3, opposite),  # weight +0.5, but opposite direction
    ]
    # total_weight (sum of |weight|) is 1.0, but the vectors cancel out —
    # exercises the norm<1e-6 guard, not the total_weight==0 guard.
    assert recommender_service.compute_user_profile(ubs) is None


def test_liked_categories_excludes_rating_below_three():
    e = _axis_vector(0)
    ubs = [
        _fake_user_book(5, e, ["Fantasia"]),
        _fake_user_book(3, e, ["Ficção Científica"]),   # boundary: 3 counts as liked
        _fake_user_book(2, e, ["Terror"]),               # boundary: 2 does not
        _fake_user_book(1, e, ["Crime"]),
        _fake_user_book(None, e, ["Aventura"]),
    ]
    liked = recommender_service.liked_categories(ubs)
    assert normalize_categories(["Fantasia"]) <= liked
    assert normalize_categories(["Ficção Científica"]) <= liked
    assert normalize_categories(["Aventura"]) <= liked
    assert not (normalize_categories(["Terror"]) & liked)
    assert not (normalize_categories(["Crime"]) & liked)


def test_top_interests_excludes_disliked_authors_and_categories():
    e = _axis_vector(0)
    ubs = [
        _fake_user_book(5, e, ["Fantasia"], author="Autora Amada"),
        _fake_user_book(None, e, ["Fantasia"], author="Autora Amada"),
        _fake_user_book(3, e, ["Fantasia"], author="Autora Neutra"),  # boundary: still positive
        _fake_user_book(1, e, ["Terror"], author="Autor Odiado"),
        _fake_user_book(2, e, ["Terror"], author="Autor Odiado"),
    ]
    authors, categories = recommender_service.top_interests(ubs, n_authors=5, n_categories=5)
    assert "Autora Amada" in authors
    assert "Autora Neutra" in authors
    assert "Autor Odiado" not in authors
    assert "Fantasia" in categories
    assert "Terror" not in categories
    # Weighted count: 2.5 (5*) + 1.0 (unrated) > 0.5 (3*) -> loved author ranks first
    assert authors[0] == "Autora Amada"


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


def test_low_rating_repels_similar_books(client):
    baseline = client.get("/api/recommendations", params={"limit": 10}).json()
    sem_before = {x["title"]: x["semantic_score"] for x in baseline}
    assert "O Cosmos Explicado" in sem_before

    # User reads a science book and hates it
    r = client.post("/api/books", json={
        "title": "Física do Cosmos", "author": "E. Ciência",
        "description": "Ciência e física do cosmos.", "categories": ["Science"],
        "status": "read", "rating": 1,
    })
    assert r.status_code == 201, r.text

    after = client.get("/api/recommendations", params={"limit": 10}).json()
    sem_after = {x["title"]: x["semantic_score"] for x in after}

    # Science candidate is pushed away from the profile; fantasy stays on top
    assert sem_after["O Cosmos Explicado"] < sem_before["O Cosmos Explicado"]
    assert after[0]["title"] in ("A Torre dos Dragões", "Reinos de Magia")
    assert after[-1]["title"] == "O Cosmos Explicado"


def test_cumulative_dislikes_repel_further(client):
    before = {x["title"]: x["semantic_score"] for x in client.get("/api/recommendations", params={"limit": 10}).json()}

    # A second, unrelated science book that the user also hates
    r = client.post("/api/books", json={
        "title": "Física Quântica para Todos", "author": "F. Ciência",
        "description": "Mais ciência e física do cosmos, agora com quântica.",
        "categories": ["Science"], "status": "read", "rating": 1,
    })
    assert r.status_code == 201, r.text

    after = {x["title"]: x["semantic_score"] for x in client.get("/api/recommendations", params={"limit": 10}).json()}
    # A second dislike in the same topic pushes the candidate away further, not less
    assert after["O Cosmos Explicado"] < before["O Cosmos Explicado"]


def test_wishlist_books_do_not_affect_profile_or_candidates(client):
    before = client.get("/api/recommendations", params={"limit": 10}).json()
    catalog_size_before = recommender_service.size

    r = client.post("/api/books", json={
        "title": "Quero Ler Isso Um Dia", "author": "Z. Desconhecido",
        "description": "Um livro qualquer só para a lista de desejos.",
        "categories": ["Fiction"], "status": "wishlist",
    })
    assert r.status_code == 201, r.text

    # Wishlist books don't build the profile (status filter) and aren't
    # candidates either (they're not added to the CacheBook/FAISS index).
    after = client.get("/api/recommendations", params={"limit": 10}).json()
    assert [x["title"] for x in before] == [x["title"] for x in after]
    assert [x["score"] for x in before] == [x["score"] for x in after]
    assert recommender_service.size == catalog_size_before
