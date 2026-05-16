import logging
import re
from typing import List

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """診斷期：跳過 PDF 處理，避免引用報錯"""
    return "診斷模式：PDF 處理已暫時關閉"

def chunk_text(
    text: str,
    document_id: str,
    subject_id: str,
    unit_code: str,
    document_type: str,
    source_filename: str,
) -> List[dict]:
    """診斷期：回傳固定 chunk"""
    return []

def _clean_text(text: str) -> str:
    return text.strip()
