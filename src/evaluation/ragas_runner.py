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
    # ragas 0.4.3: _LLM* classes are private but are the correct ones for evaluate()
    # The public ragas.metrics.collections API uses @experiment(), not evaluate()
    from ragas.metrics import (
        _LLMContextPrecisionWithReference as ContextPrecision,
        _LLMContextRecall as ContextRecall,
        _Faithfulness as Faithfulness,
        _ResponseRelevancy as AnswerRelevancy,
    )

    class _EmbeddingsWithQuery(RagasHFEmbeddings):
        """LangChain-compatible shim that ResponseRelevancy needs."""
        def embed_query(self, text: str) -> list[float]:
            return self.embed_text(text)
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self.embed_texts(texts)
        async def aembed_query(self, text: str) -> list[float]:
            return await self.aembed_text(text)
        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return await self.aembed_texts(texts)

    def _build_llm_groq():
        import instructor
        from groq import Groq
        client = instructor.from_groq(Groq(api_key=groq_api_key), mode=instructor.Mode.JSON)
        return llm_factory(groq_model, provider="groq", client=client)

    def _build_llm_gemini():
        import instructor
        import google.genai as genai
        import ragas.llms.base as _ragas_base
        # ragas hardcodes GEMINI_TOOLS (function calling) for google.genai clients.
        # Flash Lite doesn't support function calling — patch to use GEMINI_JSON
        # (response_mime_type=application/json) which Flash Lite handles correctly.
        _orig = _ragas_base._get_instructor_client
        def _patched(client, provider):
            if provider.lower() in ("google", "gemini"):
                return instructor.from_genai(client, mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS)
            return _orig(client, provider)
        _ragas_base._get_instructor_client = _patched
        try:
            client = genai.Client(api_key=google_api_key)
            return llm_factory(gemini_model, provider="google", client=client)
        finally:
            _ragas_base._get_instructor_client = _orig

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

    def _make_metrics(llm):
        m = [Faithfulness(llm=llm), AnswerRelevancy(llm=llm, embeddings=ragas_emb)]
        if has_reference:
            m += [ContextPrecision(llm=llm), ContextRecall(llm=llm)]
        return m

    scores = {}
    providers = []
    if google_api_key:
        providers.append(("gemini", _build_llm_gemini))
    if groq_api_key:
        providers.append(("groq", _build_llm_groq))
    if not providers:
        raise RuntimeError("run_ragas: no API key provided")

    for provider_name, build_fn in providers:
        try:
            llm = build_fn()
            result = evaluate(dataset, metrics=_make_metrics(llm), show_progress=False)
            scores = result.to_pandas().iloc[0].to_dict()
            break
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
                print(f"[ragas] {provider_name} rate-limited — falling back to next provider")
                continue
            print(f"[ragas] evaluate() failed on {provider_name}: {e}")
            break

    return {
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
    google_api_key = os.getenv("GOOGLE_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # Always try Groq first for RAGAS — GENERATION_PROVIDER only controls generator.py
    groq_api_key = os.getenv("GROQ_API_KEY")
    # RAGAS_GEMINI_MODEL is separate from GEMINI_MODEL — Flash Lite doesn't support
    # instructor's structured output mode (returns markdown JSON instead of function calls)
    gemini_model = os.getenv("RAGAS_GEMINI_MODEL", "gemini-2.5-flash")

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
