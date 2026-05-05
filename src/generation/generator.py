import os
from typing import Any
from dotenv import load_dotenv

SYSTEM_PROMPT = """You are an expert on Indian financial regulations (RBI and SEBI).
Answer the question using ONLY the provided passages. Cite passage numbers like [1], [2].
If the answer is not in the passages, say "Not found in the provided context." Do not hallucinate."""

def _build_user_prompt(query: str, chunks: list[dict]) -> str:
    passages = "\n\n".join(
        f"[{i+1}] (Source: {c['doc_id']}, Page {c['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    return f"Passages:\n{passages}\n\nQuestion: {query}"

def generate(
    query: str,
    chunks: list[dict],
    groq_api_key: str | None = None,
    google_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    gemini_model: str = "gemini-2.5-flash",
) -> dict[str, Any]:
    last_exception = None

    # 1. Try Groq
    if groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            user_prompt = _build_user_prompt(query, chunks)
            
            response = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=512,
                temperature=0.1,
            )
            
            return {
                "answer": response.choices[0].message.content,
                "token_cost": response.usage.total_tokens if response.usage else 0,
                "model_used": groq_model,
            }
        except Exception as e:
            last_exception = e

    # 2. Fallback to Gemini (with retry + model fallback on 503)
    import time
    import google.genai as genai
    client = genai.Client(api_key=google_api_key)
    user_prompt = _build_user_prompt(query, chunks)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    gemini_candidates = [gemini_model, "gemini-2.0-flash"]
    for model_candidate in gemini_candidates:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=full_prompt,
                )
                token_cost = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_cost = response.usage_metadata.total_token_count
                return {
                    "answer": response.text,
                    "token_cost": token_cost,
                    "model_used": model_candidate,
                }
            except Exception as e:
                last_exception = e
                err = str(e)
                if "503" in err or "UNAVAILABLE" in err or "high demand" in err:
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s
                    continue
                break  # non-503 error — skip retries, try next model

    if last_exception:
        raise last_exception
    
    raise RuntimeError("Generation failed: No API keys provided or models failed.")

def generate_from_env(query: str, chunks: list[dict]) -> dict[str, Any]:
    load_dotenv()

    google_api_key = os.getenv("GOOGLE_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Set GENERATION_PROVIDER=gemini in .env to skip Groq (e.g. when rate limited)
    provider = os.getenv("GENERATION_PROVIDER", "groq").lower()
    groq_api_key = os.getenv("GROQ_API_KEY") if provider != "gemini" else None

    return generate(
        query=query,
        chunks=chunks,
        groq_api_key=groq_api_key,
        google_api_key=google_api_key,
        groq_model=groq_model,
        gemini_model=gemini_model,
    )
