"""
models/question.py — AI 生成題目的核心資料結構
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    TEXTBOOK = "textbook"
    PAST_EXAM = "past_exam"


class GenerationMode(str, Enum):
    PRINT = "print"    # 模式A：輸出 Word 檔
    QUIZ = "quiz"      # 模式B：手機刷題


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


# ── 題目相關 ──────────────────────────────────────────────────

class Choice(BaseModel):
    key: str = Field(..., pattern="^[ABCD]$")
    text: str

class Question(BaseModel):
    id: int
    question: str
    choices: List[Choice] = Field(..., min_length=4, max_length=4)
    answer: str = Field(..., pattern="^[ABCD]$")
    explanation: str
    unit_code: Optional[str] = "1-1"
    section: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)

    @field_validator("choices")
    @classmethod
    def validate_choice_keys(cls, v: list) -> list:
        keys = {c.key for c in v}
        assert keys == {"A", "B", "C", "D"}, "選項必須包含完整的 A、B、C、D"
        return v


class ExamResult(BaseModel):
    subject: str
    subject_id: str
    units: List[str]
    total_questions: int
    questions: List[Question]
    generated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[dict] = None


# ── 生成請求 ──────────────────────────────────────────────────

class ExamGenerateRequest(BaseModel):
    subject_id: str
    unit_codes: List[str] = Field(..., min_length=1)
    question_count: int = Field(default=20, ge=5, le=50)
    mode: GenerationMode = GenerationMode.QUIZ
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)


# ── 科目/單元 ─────────────────────────────────────────────────

class UnitCreate(BaseModel):
    name: str
    unit_code: str  # e.g. "1-1"
    description: Optional[str] = ""

class SubjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class SubjectOut(SubjectCreate):
    id: str
    created_at: Optional[datetime] = None

class UnitOut(UnitCreate):
    id: str
    subject_id: str
    created_at: Optional[datetime] = None


# ── 文件 ──────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    subject_id: str
    unit_ids: List[str]
    document_type: DocumentType
    filename: str
    storage_path: str
    status: DocumentStatus
    chunk_count: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
