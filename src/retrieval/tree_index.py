import os
from src.retrieval.base import BaseRetriever, Chunk, RetrievalResult


def _make_llm():
    """Return Groq LLM if GROQ_API_KEY is set, otherwise fall back to Gemini."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        from llama_index.llms.groq import Groq as LlamaGroq
        return LlamaGroq(model="llama-3.3-70b-versatile", api_key=groq_key)

    google_key = os.getenv("GOOGLE_API_KEY", "")
    if google_key:
        from llama_index.llms.google_genai import GoogleGenAI
        return GoogleGenAI(model="gemini-2.5-flash", api_key=google_key)

    raise RuntimeError(
        "No LLM available: set GROQ_API_KEY (preferred) or GOOGLE_API_KEY in .env"
    )


class TreeIndexRetriever(BaseRetriever):
    """LlamaIndex TreeIndex retriever. Uses Groq (llama-3.3-70b) by default;
    falls back to Gemini 2.5 Flash if only GOOGLE_API_KEY is set."""

    def __init__(self, chunks: list[Chunk], api_key: str | None = None):
        super().__init__(chunks)
        # api_key kept for backwards-compat; LLM selection handled by _make_llm()
        self.api_key = api_key
        self._index = None
        self._query_engine = None

    def build_index(self) -> None:
        from llama_index.core import Settings, Document, TreeIndex

        Settings.llm = _make_llm()
        Settings.embed_model = "local:all-MiniLM-L6-v2"
        Settings.chunk_size = 512
        Settings.chunk_overlap = 64

        documents = [
            Document(
                text=c["text"],
                metadata={
                    "id": c["id"],
                    "doc_id": c["doc_id"],
                    "page": c["page"],
                    "section": c["section"],
                },
            )
            for c in self.chunks
        ]

        self._index = TreeIndex.from_documents(documents)
        self._query_engine = self._index.as_query_engine(retriever_mode="select_leaf")

    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        if not self._query_engine:
            raise RuntimeError("Index not built. Call build_index() or load_index() first.")

        response = self._query_engine.query(query)

        token_cost = 0
        try:
            usage = response.metadata.get("usage_metadata", {})
            token_cost = usage.get("total_token_count", 0)
        except Exception:
            token_cost = 0

        retrieved_chunks = []
        for node in response.source_nodes[:k]:
            meta = node.metadata or {}
            retrieved_chunks.append(
                Chunk(
                    id=meta.get("id", node.node_id),
                    text=node.text,
                    doc_id=meta.get("doc_id", ""),
                    page=meta.get("page", 0),
                    section=meta.get("section", ""),
                )
            )

        return RetrievalResult(
            strategy="tree_index",
            chunks=retrieved_chunks,
            latency_ms=0.0,
            token_cost=token_cost,
        )

    def save_index(self, path: str) -> None:
        if not self._index:
            raise RuntimeError("No index to save.")
        os.makedirs(path, exist_ok=True)
        self._index.storage_context.persist(persist_dir=path)

    def load_index(self, path: str) -> None:
        from llama_index.core import StorageContext, load_index_from_storage, Settings

        Settings.llm = _make_llm()
        Settings.embed_model = "local:all-MiniLM-L6-v2"

        storage_context = StorageContext.from_defaults(persist_dir=path)
        self._index = load_index_from_storage(storage_context)
        self._query_engine = self._index.as_query_engine(retriever_mode="select_leaf")
