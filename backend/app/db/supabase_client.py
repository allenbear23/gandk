"""
db/supabase_client.py — Supabase 統一客戶端（Singleton）

職責：
- PostgreSQL CRUD（科目、單元、文件元資料）
- Supabase Storage（PDF 上傳/下載）
- pgvector 向量搜尋（取代 ChromaDB）
"""
from supabase import create_client, Client
from app.config import get_settings
import logging
import uuid
from typing import List, Optional

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Singleton Supabase 客戶端"""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("請在 .env 設定 SUPABASE_URL 和 SUPABASE_KEY")

    _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    logger.info("✅ Supabase 客戶端初始化成功")
    return _supabase_client


# ══════════════════════════════════════════════════
#  科目 CRUD
# ══════════════════════════════════════════════════

async def get_all_subjects() -> list[dict]:
    sb = get_supabase()
    res = sb.table("subjects").select("*").order("created_at").execute()
    return res.data


async def create_subject(data: dict) -> str:
    sb = get_supabase()
    res = sb.table("subjects").insert(data).execute()
    return res.data[0]["id"]


async def get_subject_name(subject_id: str) -> str:
    sb = get_supabase()
    res = sb.table("subjects").select("name").eq("id", subject_id).single().execute()
    return res.data["name"] if res.data else subject_id


async def delete_subject(subject_id: str):
    sb = get_supabase()
    sb.table("subjects").delete().eq("id", subject_id).execute()


# ══════════════════════════════════════════════════
#  單元 CRUD
# ══════════════════════════════════════════════════

async def get_units_by_subject(subject_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("units")
        .select("*")
        .eq("subject_id", subject_id)
        .order("unit_code")
        .execute()
    )
    return res.data


async def create_unit(subject_id: str, data: dict) -> str:
    sb = get_supabase()
    data["subject_id"] = subject_id
    res = sb.table("units").insert(data).execute()
    return res.data[0]["id"]


# ══════════════════════════════════════════════════
#  文件 CRUD
# ══════════════════════════════════════════════════

async def create_document_record(data: dict) -> str:
    sb = get_supabase()
    res = sb.table("documents").insert(data).execute()
    return res.data[0]["id"]


async def update_document_status(doc_id: str, status: str, extra: dict = None):
    sb = get_supabase()
    update_data = {"status": status}
    if extra:
        update_data.update(extra)
    sb.table("documents").update(update_data).eq("id", doc_id).execute()


async def get_all_documents(subject_id: str = None) -> list[dict]:
    sb = get_supabase()
    query = sb.table("documents").select("*").order("uploaded_at", desc=True)
    if subject_id:
        query = query.eq("subject_id", subject_id)
    return query.execute().data


async def get_document_by_id(doc_id: str) -> Optional[dict]:
    sb = get_supabase()
    res = sb.table("documents").select("*").eq("id", doc_id).single().execute()
    return res.data


# ══════════════════════════════════════════════════
#  Storage — PDF 上傳/下載
# ══════════════════════════════════════════════════

async def upload_pdf_to_storage(
    file_bytes: bytes,
    filename: str,
    subject_id: str,
    document_type: str,
) -> str:
    """
    上傳 PDF 到 Supabase Storage。
    回傳 storage path（相對於 bucket 根目錄）。
    """
    settings = get_settings()
    sb = get_supabase()
    unique_id = uuid.uuid4().hex[:8]
    storage_path = f"{subject_id}/{document_type}/{unique_id}_{filename}"

    try:
        # 注意：Supabase Python SDK 的 upsert 是在 file_options 裡的 "upsert" 鍵
        res = sb.storage.from_(settings.supabase_storage_bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true"
            },
        )
        # 檢查是否回傳了錯誤 (有些版本會回傳錯誤物件而非噴例外)
        if hasattr(res, 'error') and res.error:
            raise Exception(f"Supabase Storage 錯誤: {res.error}")
            
        logger.info(f"✅ PDF 上傳成功: {storage_path}")
        return storage_path
    except Exception as e:
        logger.error(f"❌ Storage 上傳失敗: {str(e)}")
        raise Exception(f"無法存取 Storage (請確認 bucket 'exam-pdfs' 是否已建立): {str(e)}")


async def download_pdf_from_storage(storage_path: str) -> bytes:
    settings = get_settings()
    sb = get_supabase()
    return sb.storage.from_(settings.supabase_storage_bucket).download(storage_path)


# ══════════════════════════════════════════════════
#  pgvector — 向量 CRUD（取代 ChromaDB）
# ══════════════════════════════════════════════════

async def insert_chunks_to_pgvector(chunks: List[dict], embeddings: List[List[float]]):
    """
    批次將 chunks + embeddings 寫入 document_chunks 表。
    使用 upsert 確保冪等性（重新索引時自動覆蓋）。
    """
    sb = get_supabase()
    rows = []
    for chunk, emb in zip(chunks, embeddings):
        meta = chunk["metadata"]
        rows.append({
            "id": chunk["id"],
            "document_id": meta["document_id"],
            "subject_id": meta["subject_id"],
            "unit_code": meta["unit_code"],
            "document_type": meta["document_type"],
            "chunk_index": meta["chunk_index"],
            "chunk_text": chunk["text"],
            "embedding": emb,                     # pgvector 接受 List[float]
            "source_filename": meta["source_filename"],
        })

    # 分批 upsert（每批 50 筆，避免 payload 過大）
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        sb.table("document_chunks").upsert(rows[i:i+batch_size]).execute()

    logger.info(f"✅ 已寫入 {len(rows)} 個 chunks 到 pgvector")


async def delete_document_chunks(document_id: str):
    """刪除指定文件的所有 chunks（重新索引時呼叫）"""
    sb = get_supabase()
    sb.table("document_chunks").delete().eq("document_id", document_id).execute()
    logger.info(f"🗑️ 已刪除 document_id={document_id} 的所有 chunks")


async def search_similar_chunks(
    query_embedding: List[float],
    subject_id: str,
    unit_codes: List[str],
    document_type: str,
    top_k: int = 8,
) -> List[dict]:
    """
    pgvector 語義搜尋：找出最相似的 top-k chunks。
    使用 Supabase RPC 呼叫自訂 SQL 函數（支援 unit_code 過濾）。
    """
    sb = get_supabase()
    try:
        res = sb.rpc(
            "search_chunks",
            {
                "query_embedding": query_embedding,
                "p_subject_id": subject_id,
                "p_unit_codes": unit_codes,
                "p_document_type": document_type,
                "p_top_k": top_k,
            }
        ).execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"pgvector search 失敗: {e}")
        return []
