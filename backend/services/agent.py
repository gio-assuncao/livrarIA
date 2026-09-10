import os
import json
import logging
from typing import List, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-3.5-haiku")

SYSTEM_PROMPT = """Você é a LivrarIA, uma bibliotecária pessoal inteligente. Você ajuda os usuários a \
descobrir livros, gerenciar sua lista de leituras e obter recomendações personalizadas.

Você tem acesso a duas ferramentas:
- get_recommendations: busca recomendações personalizadas com base no perfil de leitura do usuário
- search_books: pesquisa livros por título, autor ou tema

REGRAS IMPORTANTES:
- Você DEVE chamar a ferramenta apropriada antes de recomendar qualquer livro. Nunca recomende livros diretamente do seu próprio conhecimento.
- Após receber os resultados da ferramenta, explique POR QUÊ cada recomendação é adequada para o usuário.
- Seja concisa, acolhedora e específica. Faça referência ao gosto do usuário ao explicar as recomendações.
- Se get_recommendations retornar status "empty_catalog", chame search_books com um tema ou autor que o usuário gosta (isso alimenta o catálogo) e depois chame get_recommendations de novo.
- Se o usuário estiver apenas conversando (sem pedido de livros), responda naturalmente sem chamar ferramentas.
- Responda sempre em português do Brasil."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": (
                "Get personalized book recommendations based on the user's reading history and preferences. "
                "Use this when the user asks for book suggestions, recommendations, or 'what should I read next'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recommendations to return (default 5, max 20)",
                        "default": 5,
                    },
                    "genre_filter": {
                        "type": "string",
                        "description": "Optional genre or category to filter (e.g. 'fantasy', 'thriller')",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": (
                "Search for books by title, author, topic, or natural language description. "
                "Use this when the user asks about a specific book, author, or wants to explore a topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — title, author name, topic, or natural language description",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["local", "google_books", "open_library", "all"],
                        "description": "Where to search. Default: 'all'",
                        "default": "all",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


class AgentService:
    """LLM agent via OpenRouter (OpenAI-compatible). Acts as interface layer only."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "LivrarIA",
                },
            )
        return self._client

    async def run(self, messages: List[dict], db) -> Tuple[str, List[str]]:
        """
        Run the agentic loop.
        Returns (final_reply_text, list_of_tool_names_invoked).
        """
        from services.recommender import recommender_service
        from services.external_api import external_api_service

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation += [{"role": m["role"], "content": m["content"]} for m in messages]

        tools_invoked: List[str] = []
        max_rounds = 5

        for _ in range(max_rounds):
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=conversation,
                tools=TOOLS,
                tool_choice="auto",
            )

            choice = response.choices[0]
            message = choice.message

            # Append assistant turn to conversation
            conversation.append(message)

            if choice.finish_reason == "tool_calls" and message.tool_calls:
                tool_results = []
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tools_invoked.append(tool_name)
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    result_text = await self._execute_tool(
                        tool_name, tool_input, db, recommender_service, external_api_service
                    )

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })

                conversation.extend(tool_results)
                continue

            # stop — return final text
            return message.content or "", tools_invoked

        return "I'm sorry, I couldn't process your request right now. Please try again.", tools_invoked

    async def _execute_tool(
        self, tool_name: str, tool_input: dict, db, recommender_service, external_api_service
    ) -> str:
        if tool_name == "get_recommendations":
            return await self._get_recommendations(tool_input, db, recommender_service)
        elif tool_name == "search_books":
            return await self._search_books(tool_input, db, external_api_service)
        return "Tool not found."

    async def _get_recommendations(self, tool_input: dict, db, recommender_service) -> str:
        from models import UserBook

        limit = tool_input.get("limit", 5)
        genre_filter = tool_input.get("genre_filter")

        user_books = (
            db.query(UserBook)
            .filter(UserBook.status.in_(["read", "reading"]))
            .all()
        )

        if not user_books:
            return json.dumps({
                "status": "no_history",
                "message": "The user has no read/reading books yet. Suggest they add some books first.",
                "recommendations": [],
            })

        user_profile = recommender_service.compute_user_profile(user_books)
        if user_profile is None:
            return json.dumps({
                "status": "no_embeddings",
                "message": "User has books but embeddings could not be computed.",
                "recommendations": [],
            })

        recs = recommender_service.hybrid_rank(
            user_profile=user_profile,
            limit=min(int(limit or 5), 20),
            db=db,
            genre_filter=genre_filter,
            liked=recommender_service.liked_categories(user_books),
        )

        if not recs:
            return json.dumps({
                "status": "empty_catalog",
                "message": (
                    "The catalog has no candidates yet. Call search_books with a topic or author "
                    "the user likes, then call get_recommendations again."
                ),
                "recommendations": [],
            })

        return json.dumps({
            "status": "ok",
            "count": len(recs),
            "recommendations": [r.model_dump() for r in recs],
        })

    async def _search_books(self, tool_input: dict, db, external_api_service) -> str:
        from models import Book

        query = tool_input.get("query", "")
        source = tool_input.get("source", "all")

        results = []

        if source in ("local", "all"):
            local_books = (
                db.query(Book)
                .filter(
                    (Book.title.ilike(f"%{query}%")) | (Book.author.ilike(f"%{query}%"))
                )
                .limit(5)
                .all()
            )
            for b in local_books:
                results.append({
                    "source": "local",
                    "title": b.title,
                    "author": b.author,
                    "description": b.description,
                    "categories": b.categories or [],
                })

        if source in ("google_books", "open_library", "all"):
            from services.catalog import cache_results
            external = await external_api_service.search(query, source)
            await cache_results(db, external)  # grows the recommendation catalog
            for r in external[:8]:
                results.append({
                    "source": r.source,
                    "external_id": r.external_id,
                    "title": r.title,
                    "author": r.author,
                    "description": r.description,
                    "categories": r.categories,
                })

        return json.dumps({
            "status": "ok",
            "query": query,
            "count": len(results),
            "books": results,
        })


agent_service = AgentService()
