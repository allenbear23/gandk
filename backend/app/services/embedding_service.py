import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings
import logging
from typing import List
import asyncio

logger = logging.getLogger(__name__)

_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        # 修正：改用 text-embedding-004 以匹配 SQL Schema 的 768 維度
        _embedding_model = "models/text-embedding-004"
        logger.info("✅ Embedding 模型 (text-embedding-004, 768維) 初始化完成")
    return _embedding_model

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
    """將查詢文字向量化"""
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
        # 回傳一個全零向量作為 fallback，避免讓整個 API 崩潰
        return [0.0] * 768
