from fastapi import APIRouter
import logging

router = APIRouter(prefix="/admin/subjects", tags=["Admin - 科目管理"])
logger = logging.getLogger(__name__)

@router.get("/", summary="取得科目清單")
async def get_subjects():
    # 診斷期：直接回傳假資料，排除資料庫與 AI 干擾
    return [
        {"id": "test-1", "name": "診斷模式 - 數學"},
        {"id": "test-2", "name": "診斷模式 - 英文"}
    ]

@router.get("/debug-models", summary="診斷：列出可用模型")
async def debug_models():
    return [{"name": "診斷模式已開啟"}]
