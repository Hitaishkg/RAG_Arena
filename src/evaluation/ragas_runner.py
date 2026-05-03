import os
from typing import Any
from dotenv import load_dotenv


def run_ragas(
    query: str,
    retrieved_chunks: list[dict[str, Any]],
    generated_answer: str,
    ground_truth: str,
    groq_api_key: str | None = None,
    google_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    gemini_model: str = "gemini-2.5-flash",
) -> dict[str, float]:
    from ragas import evaluate, EvaluationDataset, SingleTurnSample
    from ragas.llms import llm_factory
    from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
    from ragas.metrics import (
        _LLMContextPrecisionWithReference as ContextPrecision,
        _LLMContextRecall as ContextRecall,
        _Faithfulness as Faithfulness,
        _ResponseRelevancy as AnswerRelevancy,
    )

    class _EmbeddingsWithQuery(RagasHFEmbeddings):
        """Add LangChain-compatible interface that ResponseRelevancy needs."""
        def embed_query(self, text: str) -> list[float]:
            return self.embed_text(text)

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self.embed_texts(texts)

        async def aembed_query(self, text: str) -> list[float]:
            return await self.aembed_text(text)

        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return await self.aembed_texts(texts)

    def _build_llm():
        if groq_api_key:
            import instructor
            from groq import Groq
            client = instructor.from_groq(Groq(api_key=groq_api_key), mode=instructor.Mode.JSON)
            return llm_factory(groq_model, provider="groq", client=client)
        if google_api_key:
            import google.genai as genai
            client = genai.Client(api_key=google_api_key)
            return llm_factory(gemini_model, provider="google", client=client)
        raise RuntimeError("run_ragas: no API key provided")

    ragas_llm = _build_llm()
    ragas_emb = _EmbeddingsWithQuery(model="all-MiniLM-L6-v2")

    context_texts = [c["text"] for c in retrieved_chunks]
    has_reference = bool(ground_truth.strip())
    sample = SingleTurnSample(
        user_input=query,
        retrieved_contexts=context_texts,
        response=generated_answer,
        reference=ground_truth if has_reference else None,
    )
    dataset = EvaluationDataset(samples=[sample])

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_emb),
    ]
    if has_reference:
        metrics += [
            ContextPrecision(llm=ragas_llm),
            ContextRecall(llm=ragas_llm),
        ]

    try:
        result = evaluate(dataset, metrics=metrics, show_progress=False)
        scores = result.to_pandas().iloc[0].to_dict()
    except Exception:
        scores = {}

    return {
        # ragas 0.4.3: ContextPrecision produces "llm_context_precision_with_reference"
        "context_precision": float(scores.get("llm_context_precision_with_reference", 0.0)),
        "context_recall": float(scores.get("context_recall", 0.0)),
        "faithfulness": float(scores.get("faithfulness", 0.0)),
        "answer_relevance": float(scores.get("answer_relevancy", 0.0)),
    }


def run_ragas_from_env(
    query: str,
    chunks: list[dict[str, Any]],
    answer: str,
    ground_truth: str,
) -> dict[str, float]:
    load_dotenv()
    provider = os.getenv("GENERATION_PROVIDER", "groq").lower()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Respect GENERATION_PROVIDER — skip Groq when set to gemini
    groq_api_key = os.getenv("GROQ_API_KEY") if provider != "gemini" else None

    return run_ragas(
        query=query,
        retrieved_chunks=chunks,
        generated_answer=answer,
        ground_truth=ground_truth,
        groq_api_key=groq_api_key,
        google_api_key=google_api_key,
        groq_model=groq_model,
        gemini_model=gemini_model,
    )
