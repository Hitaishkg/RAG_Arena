import os
from src.retrieval.base import BaseRetriever, Chunk, RetrievalResult

class TreeIndexRetriever(BaseRetriever):
    """LlamaIndex TreeIndex retriever backed by Gemini 1.5 Flash."""

    def __init__(self, chunks: list[Chunk], api_key: str | None = None):
        super().__init__(chunks)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._index = None
        self._query_engine = None

    def build_index(self) -> None:
        """Build TreeIndex using LlamaIndex and Gemini."""
        from llama_index.core import Settings, Document, TreeIndex
        from llama_index.llms.google_genai import GoogleGenAI

        # Configure Settings
        Settings.llm = GoogleGenAI(
            model="gemini-2.5-flash",
            api_key=self.api_key,
        )
        Settings.embed_model = "local:all-MiniLM-L6-v2"
        Settings.chunk_size = 512
        Settings.chunk_overlap = 64

        # Convert chunks to LlamaIndex Documents
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

        # Build TreeIndex
        self._index = TreeIndex.from_documents(documents)
        self._query_engine = self._index.as_query_engine(retriever_mode="select_leaf")

    def retrieve(self, query: str, k: int = 5) -> RetrievalResult:
        """Retrieve top-k chunks for query."""
        if not self._query_engine:
            raise RuntimeError("Index not built. Call build_index() or load_index() first.")

        response = self._query_engine.query(query)

        # Extract token cost from response metadata if available
        token_cost = 0
        try:
            usage = response.metadata.get("usage_metadata", {})
            token_cost = usage.get("total_token_count", 0)
        except Exception:
            token_cost = 0

        # Extract source nodes as chunks
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
        """Persist using LlamaIndex storage context."""
        if not self._index:
            raise RuntimeError("No index to save.")
        
        os.makedirs(path, exist_ok=True)
        self._index.storage_context.persist(persist_dir=path)

    def load_index(self, path: str) -> None:
        """Load from storage."""
        from llama_index.core import StorageContext, load_index_from_storage, Settings
        from llama_index.llms.google_genai import GoogleGenAI

        Settings.llm = GoogleGenAI(model="gemini-2.5-flash", api_key=self.api_key)
        Settings.embed_model = "local:all-MiniLM-L6-v2"
        
        storage_context = StorageContext.from_defaults(persist_dir=path)
        self._index = load_index_from_storage(storage_context)
        self._query_engine = self._index.as_query_engine(retriever_mode="select_leaf")
