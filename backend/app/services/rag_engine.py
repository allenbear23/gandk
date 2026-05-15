"""
services/rag_engine.py — RAG 檢索引擎

流程：
1. 將使用者的「範圍描述」向量化成 query embedding
2. 分別從 textbook chunks 和 past_exam chunks 做 pgvector 搜尋
3. 回傳雙來源的知識段落供 AI 使用
"""
import logging
from typing import List
from app.services.embedding_service import embed_query
from app.db.supabase_client import search_similar_chunks

logger = logging.getLogger(__name__)


async def retrieve_context(
    subject_id: str,
    unit_codes: List[str],
    subject_name: str,
    top_k: int = 8,
) -> dict:
    """
    RAG 雙來源檢索：
    - 課本知識（textbook）→ 確保知識正確、不超綱
    - 考古題範例（past_exam）→ 讓 AI 模仿題型風格

    回傳:
    {
        "textbook_chunks": [...],
        "past_exam_chunks": [...],
        "has_textbook": bool,
        "has_past_exam": bool,
    }
    """
    # 組合查詢語句（描述想要出題的主題）
    query_text = f"{subject_name} {' '.join(unit_codes)} 重要考點 知識整理"

    logger.info(f"🔍 RAG 檢索：subject={subject_id}，units={unit_codes}")

    # 向量化查詢
    query_embedding = await embed_query(query_text)

    # 並行搜尋兩個來源
    import asyncio
    textbook_task = search_similar_chunks(
        query_embedding=query_embedding,
        subject_id=subject_id,
        unit_codes=unit_codes,
        document_type="textbook",
        top_k=top_k,
    )
    past_exam_task = search_similar_chunks(
        query_embedding=query_embedding,
        subject_id=subject_id,
        unit_codes=unit_codes,
        document_type="past_exam",
        top_k=top_k // 2,  # 考古題取少一點，主要參考風格
    )

    textbook_chunks, past_exam_chunks = await asyncio.gather(
        textbook_task, past_exam_task
    )

    logger.info(
        f"  ✅ 檢索完成：課本 {len(textbook_chunks)} chunks，"
        f"考古題 {len(past_exam_chunks)} chunks"
    )

    return {
        "textbook_chunks": textbook_chunks,
        "past_exam_chunks": past_exam_chunks,
        "has_textbook": len(textbook_chunks) > 0,
        "has_past_exam": len(past_exam_chunks) > 0,
    }
