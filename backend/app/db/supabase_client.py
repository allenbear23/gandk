import logging
logger = logging.getLogger(__name__)

def get_supabase():
    """診斷期：回傳 None"""
    return None

async def get_subject_name(subject_id: str) -> str:
    return "診斷模式"

async def get_subject_style(subject_id: str) -> str:
    return "診斷模式"

async def create_document_record(data: dict):
    return "debug-doc-id"

async def update_document_status(*args, **kwargs):
    pass

async def get_all_documents(**kwargs):
    return []

async def upload_pdf_to_storage(*args, **kwargs):
    return "debug-path"

async def delete_document_chunks(*args, **kwargs):
    pass

async def insert_chunks_to_pgvector(*args, **kwargs):
    pass

async def get_document_by_id(document_id: str):
    return {"status": "debug"}
