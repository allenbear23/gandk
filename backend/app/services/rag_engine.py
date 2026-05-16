import logging
logger = logging.getLogger(__name__)

async def retrieve_context(**kwargs):
    """診斷期：回傳空內容，防止崩潰"""
    return {"textbook_chunks": [], "past_exam_chunks": []}
