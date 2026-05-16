import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings
import logging
from typing import List
import asyncio

logger = logging.getLogger(__name__)

# 使用你環境中確切存在的模型
EMBED_MODEL = "models/gemini-embedding-001"

def _get_embedding_model():
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    return EMBED_MODEL

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def _embed_single_batch(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    model = _get_embedding_model()
    try:
        result = genai.embed_content(
            model=model,
            content=texts,
            task_type=task_type,
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Embedding API 呼叫失敗: {e}")
        raise

async def embed_chunks(chunks: List[dict], batch_size: int = 20) -> List[List[float]]:
    texts = [c["text"] for c in chunks]
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda b=batch: _embed_single_batch(b, "RETRIEVAL_DOCUMENT")
        )
        if isinstance(embeddings[0], float):
            embeddings = [embeddings]
        all_embeddings.extend(embeddings)
    return all_embeddings

async def embed_query(query_text: str) -> List[float]:
    try:
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: _embed_single_batch([query_text], "RETRIEVAL_QUERY")
        )
        if isinstance(embedding[0], float):
            return embedding
        return embedding[0]
    except Exception as e:
        logger.error(f"查詢向量化失敗: {e}")
        return [0.0] * 768
