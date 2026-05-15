"""
services/embedding_service.py — 文字向量化服務

使用 Gemini text-embedding-004 模型（768維，支援中文）
批次處理 + retry 機制確保穩定性
"""
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
        _embedding_model = "models/text-embedding-004"
        logger.info("✅ Embedding 模型初始化完成")
    return _embedding_model


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def _embed_single_batch(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    同步批次 Embedding（Gemini API 原生為同步）。
    task_type:
      - "RETRIEVAL_DOCUMENT": 用於索引（PDF chunks）
      - "RETRIEVAL_QUERY": 用於查詢時
    """
    model = _get_embedding_model()
    result = genai.embed_content(
        model=model,
        content=texts,
        task_type=task_type,
    )
    return result["embedding"] if len(texts) == 1 else result["embedding"]


async def embed_chunks(chunks: List[dict], batch_size: int = 20) -> List[List[float]]:
    """
    非同步批次向量化 chunks。
    - 每批最多 batch_size 個（Gemini API 限制）
    - 自動分批處理，避免超過 API 限制
    """
    texts = [c["text"] for c in chunks]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"  Embedding batch {i//batch_size + 1}，共 {len(batch)} 個 chunks...")

        # 在 executor 中執行同步 API 呼叫，避免阻塞 event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda b=batch: _embed_single_batch(b, "RETRIEVAL_DOCUMENT")
        )

        # Gemini API 單一文字回傳的格式不同，需統一處理
        if isinstance(embeddings[0], float):
            embeddings = [embeddings]

        all_embeddings.extend(embeddings)
        logger.info(f"  ✅ Batch {i//batch_size + 1} 完成")

    return all_embeddings


async def embed_query(query_text: str) -> List[float]:
    """
    將使用者的查詢文字向量化（用 RETRIEVAL_QUERY task type）
    """
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(
        None,
        lambda: _embed_single_batch([query_text], "RETRIEVAL_QUERY")
    )
    if isinstance(embedding[0], float):
        return embedding
    return embedding[0]
