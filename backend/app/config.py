"""
config.py — 全域環境設定（Vercel + Supabase 版本）
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AI
    gemini_api_key: str = ""

    # Supabase（取代 Firebase + ChromaDB）
    supabase_url: str = ""
    supabase_key: str = ""                          # service_role key（後端專用）
    supabase_storage_bucket: str = "exam-pdfs"

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # PDF Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
