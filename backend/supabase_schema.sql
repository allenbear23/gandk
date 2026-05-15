-- ================================================================
-- AI 考卷生成系統 — Supabase SQL Schema
-- 請在 Supabase Dashboard > SQL Editor 中執行此腳本
-- ================================================================

-- ① 啟用 pgvector（Supabase 預設已安裝）
CREATE EXTENSION IF NOT EXISTS vector;

-- ② 科目表
CREATE TABLE IF NOT EXISTS subjects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ③ 單元表
CREATE TABLE IF NOT EXISTS units (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id  UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    unit_code   TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(subject_id, unit_code)
);

-- ④ 文件元資料表
CREATE TABLE IF NOT EXISTS documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id    UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    unit_code     TEXT NOT NULL,
    document_type TEXT NOT NULL CHECK (document_type IN ('textbook', 'past_exam')),
    filename      TEXT NOT NULL,
    storage_path  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','processing','indexed','error')),
    chunk_count   INTEGER,
    char_count    INTEGER,
    error_message TEXT,
    uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
    indexed_at    TIMESTAMPTZ
);

-- ⑤ 向量 Chunks 表（核心）
CREATE TABLE IF NOT EXISTS document_chunks (
    id              TEXT PRIMARY KEY,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    subject_id      UUID NOT NULL,
    unit_code       TEXT NOT NULL,
    document_type   TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    embedding       vector(768),         -- Gemini text-embedding-004 = 768 維
    source_filename TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ⑥ 生成紀錄（可選）
CREATE TABLE IF NOT EXISTS generation_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id     UUID REFERENCES subjects(id),
    unit_codes     TEXT[] NOT NULL,
    mode           TEXT NOT NULL CHECK (mode IN ('print', 'quiz')),
    question_count INTEGER NOT NULL,
    questions_json JSONB,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- 索引
-- ================================================================

-- 向量索引（IVFFlat cosine，適合中等資料量 < 100萬筆）
-- 注意：需要先有資料才能建立 IVFFlat，開發初期可先不建
-- CREATE INDEX IF NOT EXISTS idx_chunks_embedding
--     ON document_chunks USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- 查詢加速索引
CREATE INDEX IF NOT EXISTS idx_chunks_subject_unit
    ON document_chunks(subject_id, unit_code);

CREATE INDEX IF NOT EXISTS idx_chunks_type
    ON document_chunks(document_id, document_type);

CREATE INDEX IF NOT EXISTS idx_docs_status
    ON documents(status);

CREATE INDEX IF NOT EXISTS idx_docs_subject
    ON documents(subject_id);

-- ================================================================
-- pgvector 搜尋函數（供後端 RPC 呼叫）
-- ================================================================

CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(768),
    p_subject_id    UUID,
    p_unit_codes    TEXT[],
    p_document_type TEXT,
    p_top_k         INTEGER DEFAULT 8
)
RETURNS TABLE (
    chunk_text      TEXT,
    unit_code       TEXT,
    document_type   TEXT,
    source_filename TEXT,
    similarity      FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.chunk_text,
        dc.unit_code,
        dc.document_type,
        dc.source_filename,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        dc.subject_id = p_subject_id
        AND dc.unit_code = ANY(p_unit_codes)
        AND dc.document_type = p_document_type
    ORDER BY dc.embedding <=> query_embedding  -- 距離升序 = 相似度降序
    LIMIT p_top_k;
END;
$$;

-- ================================================================
-- 測試資料（可選，用於開發測試）
-- ================================================================

-- INSERT INTO subjects (name, description) VALUES ('歷史', '高中歷史');
-- 執行後複製 id，再插入 units:
-- INSERT INTO units (subject_id, name, unit_code) VALUES ('<subject_id>', '1-1 台灣的史前文化', '1-1');
