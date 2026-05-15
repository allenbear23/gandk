"""
api/v1/admin/uploads.py — PDF 上傳與解析 API（Supabase 版）

流程：
POST /api/v1/admin/upload
  1. 接收 PDF + 元資料
  2. 上傳到 Supabase Storage
  3. 在 documents 表建立記錄（status=pending）
  4. BackgroundTask：萃取 → chunk → embed → pgvector
  5. 立即回傳 document_id

GET  /api/v1/admin/documents          → 列出所有文件
GET  /api/v1/admin/documents/{id}/status → 查詢解析進度
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from datetime import datetime, timezone
import logging

from app.models.question import DocumentStatus, DocumentType
from app.db.supabase_client import (
    create_document_record,
    update_document_status,
    get_all_documents,
    get_document_by_id,
    upload_pdf_to_storage,
    delete_document_chunks,
    insert_chunks_to_pgvector,
)
from app.services.pdf_processor import extract_text_from_pdf, chunk_text
from app.services.embedding_service import embed_chunks

router = APIRouter(prefix="/admin", tags=["Admin - 文件管理"])
logger = logging.getLogger(__name__)


# ── 背景解析任務 ───────────────────────────────────────────────

async def _process_pdf_background(
    document_id: str,
    pdf_bytes: bytes,
    subject_id: str,
    unit_code: str,
    document_type: str,
    filename: str,
):
    """PDF → 萃取 → Chunk → Embedding → pgvector"""
    try:
        logger.info(f"🔄 開始背景解析 document_id={document_id}")
        await update_document_status(document_id, DocumentStatus.PROCESSING)

        # Step 1: 萃取文字
        full_text = extract_text_from_pdf(pdf_bytes)
        if not full_text.strip():
            raise ValueError("PDF 萃取文字為空（可能為掃描版 PDF，需 OCR）")

        # Step 2: 切分 chunks
        chunks = chunk_text(
            text=full_text,
            document_id=document_id,
            subject_id=subject_id,
            unit_code=unit_code,
            document_type=document_type,
            source_filename=filename,
        )
        if not chunks:
            raise ValueError("Chunk 切分結果為空")

        # Step 3: 刪除舊的同文件 chunks（冪等）
        await delete_document_chunks(document_id)

        # Step 4: 批次 Embedding
        logger.info(f"  🧮 Embedding {len(chunks)} chunks...")
        embeddings = await embed_chunks(chunks)

        # Step 5: 寫入 pgvector
        await insert_chunks_to_pgvector(chunks, embeddings)

        # Step 6: 更新狀態
        await update_document_status(
            document_id,
            DocumentStatus.INDEXED,
            extra={
                "chunk_count": len(chunks),
                "char_count": sum(c["metadata"]["char_count"] for c in chunks),
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(f"✅ document_id={document_id} 索引完成，{len(chunks)} chunks")

    except Exception as e:
        logger.error(f"❌ 解析失敗 document_id={document_id}: {e}")
        await update_document_status(
            document_id,
            DocumentStatus.ERROR,
            extra={"error_message": str(e)[:500]}
        )


# ── API 端點 ──────────────────────────────────────────────────

@router.post("/upload", summary="上傳 PDF 並觸發背景解析")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    unit_code: str = Form(...),
    document_type: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "僅支援 PDF 格式")
    if document_type not in [t.value for t in DocumentType]:
        raise HTTPException(400, f"document_type 必須為 {[t.value for t in DocumentType]}")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "上傳的檔案為空")
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(400, "檔案大小超過 50MB 限制")

    # 上傳到 Supabase Storage
    storage_path = await upload_pdf_to_storage(
        file_bytes=pdf_bytes,
        filename=file.filename,
        subject_id=subject_id,
        document_type=document_type,
    )

    # 建立 Supabase documents 記錄
    document_id = await create_document_record({
        "subject_id": subject_id,
        "unit_code": unit_code,
        "document_type": document_type,
        "filename": file.filename,
        "storage_path": storage_path,
        "status": DocumentStatus.PENDING,
    })

    # 非阻塞背景解析
    background_tasks.add_task(
        _process_pdf_background,
        document_id=document_id,
        pdf_bytes=pdf_bytes,
        subject_id=subject_id,
        unit_code=unit_code,
        document_type=document_type,
        filename=file.filename,
    )

    return {
        "message": "PDF 上傳成功，背景解析中",
        "document_id": document_id,
        "filename": file.filename,
        "status": DocumentStatus.PENDING,
    }


@router.get("/documents", summary="取得所有文件列表")
async def list_documents(subject_id: str = None):
    docs = await get_all_documents(subject_id=subject_id)
    return {"documents": docs, "total": len(docs)}


@router.get("/documents/{document_id}/status", summary="查詢文件解析狀態")
async def get_document_status(document_id: str):
    doc = await get_document_by_id(document_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    return {
        "document_id": document_id,
        "status": doc.get("status"),
        "chunk_count": doc.get("chunk_count"),
        "error_message": doc.get("error_message"),
        "indexed_at": doc.get("indexed_at"),
    }
