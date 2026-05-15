"""
services/pdf_processor.py — PDF 文字萃取與分段（Chunking）

流程：
1. 接收 PDF bytes
2. 使用 pdfplumber 萃取純文字（對中文支援較好）
3. 清理文字（移除多餘空白、特殊符號）
4. 使用滑動視窗 (Sliding Window) 切分成 chunks
5. 回傳 chunks list，附帶 metadata
"""
import pdfplumber
import io
import re
import logging
from typing import List
from app.config import get_settings

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    從 PDF bytes 萃取全文純文字。
    使用 pdfplumber 逐頁萃取，對中文排版相容性較好。
    """
    full_text = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"📄 開始解析 PDF，共 {total_pages} 頁")

        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text()
                if text:
                    full_text.append(text.strip())
            except Exception as e:
                logger.warning(f"第 {i+1} 頁萃取失敗: {e}")
                continue

    raw_text = "\n\n".join(full_text)
    cleaned = _clean_text(raw_text)
    logger.info(f"✅ PDF 萃取完成，共 {len(cleaned)} 字元")
    return cleaned


def _clean_text(text: str) -> str:
    """
    清理萃取文字：
    - 移除連續多餘空行
    - 統一全形標點轉半形（可選）
    - 移除頁碼殘留
    """
    # 移除 3 個以上連續換行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除行首行尾多餘空白
    text = "\n".join(line.strip() for line in text.splitlines())
    # 移除常見頁碼樣式（純數字獨行）
    text = re.sub(r'(?m)^\d{1,3}$', '', text)
    # 移除連字符換行（英文 PDF 常見）
    text = re.sub(r'-\n', '', text)
    return text.strip()


def chunk_text(
    text: str,
    document_id: str,
    subject_id: str,
    unit_code: str,
    document_type: str,
    source_filename: str,
) -> List[dict]:
    """
    將長文字切分為固定大小的 chunks（滑動視窗法）。

    回傳格式:
    [
        {
            "id": "doc123_chunk_0",
            "text": "...",
            "metadata": { ... }
        }
    ]
    """
    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    chunks = []
    start = 0
    chunk_index = 0

    # 以句子邊界切割，避免截斷在句子中間
    sentences = _split_into_sentences(text)
    current_chunk = ""

    for sentence in sentences:
        # 若加入這個句子後超出 chunk_size，就先儲存當前 chunk
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunk_id = f"{document_id}_chunk_{chunk_index}"
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "metadata": {
                    "document_id": document_id,
                    "subject_id": subject_id,
                    "unit_code": unit_code,
                    "document_type": document_type,
                    "chunk_index": chunk_index,
                    "source_filename": source_filename,
                    "char_count": len(current_chunk)
                }
            })
            chunk_index += 1

            # 保留 overlap（最後 N 個字元）做為下一個 chunk 的開頭
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk += sentence

    # 處理最後一個 chunk
    if current_chunk.strip():
        chunks.append({
            "id": f"{document_id}_chunk_{chunk_index}",
            "text": current_chunk.strip(),
            "metadata": {
                "document_id": document_id,
                "subject_id": subject_id,
                "unit_code": unit_code,
                "document_type": document_type,
                "chunk_index": chunk_index,
                "source_filename": source_filename,
                "char_count": len(current_chunk)
            }
        })

    logger.info(f"✅ 切分完成：{len(chunks)} 個 chunks（chunk_size={chunk_size}, overlap={overlap}）")
    return chunks


def _split_into_sentences(text: str) -> List[str]:
    """
    以中文標點符號（。！？；）與換行符號作為句子邊界切分。
    保留句尾標點符號在句子末尾。
    """
    # 在中文句尾標點後插入分隔符，再 split
    pattern = r'(?<=[。！？；\n])'
    parts = re.split(pattern, text)
    return [p for p in parts if p.strip()]
