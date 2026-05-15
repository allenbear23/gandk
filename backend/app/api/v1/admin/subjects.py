"""
api/v1/admin/subjects.py — 科目與單元管理 API（Supabase 版）
"""
from fastapi import APIRouter, HTTPException
from app.models.question import SubjectCreate, SubjectOut, UnitCreate, UnitOut
from app.db.supabase_client import (
    get_all_subjects,
    get_units_by_subject,
    create_subject,
    create_unit,
    delete_subject,
)

router = APIRouter(prefix="/admin", tags=["Admin - 科目管理"])


@router.get("/subjects", summary="取得所有科目")
async def list_subjects():
    subjects = await get_all_subjects()
    return {"subjects": subjects}


@router.post("/subjects", summary="新增科目")
async def add_subject(data: SubjectCreate):
    subject_id = await create_subject(data.model_dump())
    return {"id": subject_id, **data.model_dump()}


@router.get("/subjects/{subject_id}/units", summary="取得科目下的所有單元")
async def list_units(subject_id: str):
    units = await get_units_by_subject(subject_id)
    return {"subject_id": subject_id, "units": units}


@router.post("/subjects/{subject_id}/units", summary="新增單元")
async def add_unit(subject_id: str, data: UnitCreate):
    unit_id = await create_unit(subject_id, data.model_dump())
    return {"id": unit_id, "subject_id": subject_id, **data.model_dump()}


@router.delete("/subjects/{subject_id}", summary="刪除科目（含所有單元、文件）")
async def remove_subject(subject_id: str):
    await delete_subject(subject_id)
    return {"message": f"科目 {subject_id} 已刪除"}
