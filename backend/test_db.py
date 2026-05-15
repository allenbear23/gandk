import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

# 加載 .env
load_dotenv(dotenv_path="/Users/allen/Desktop/AI-Exam-Generator/backend/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

async def check_db():
    print(f"🔍 正在連線到: {url}")
    try:
        supabase: Client = create_client(url, key)
        
        # 1. 檢查 Subjects 表
        print("\n--- [1] Subjects Table ---")
        sub_res = supabase.table("subjects").select("count", count="exact").limit(1).execute()
        print(f"✅ 成功! 目前科目數量: {sub_res.count}")

        # 2. 檢查 Units 表
        print("\n--- [2] Units Table ---")
        unit_res = supabase.table("units").select("count", count="exact").limit(1).execute()
        print(f"✅ 成功! 目前單元數量: {unit_res.count}")

        # 3. 檢查 Documents 表欄位
        print("\n--- [3] Documents Table Structure ---")
        doc_res = supabase.table("documents").select("*").limit(1).execute()
        if len(doc_res.data) >= 0:
            print("✅ 成功連線到 Documents 表")
            # 檢查是否有 subject_id 欄位 (透過檢查回傳資料或嘗試查詢)
            try:
                supabase.table("documents").select("subject_id").limit(1).execute()
                print("✅ 欄位 'subject_id' 存在")
            except Exception:
                print("❌ 欄位 'subject_id' 不存在! 請執行 SQL 修正。")

        # 4. 檢查 Chunks 表
        print("\n--- [4] Document Chunks (Vector) ---")
        chunk_res = supabase.table("document_chunks").select("count", count="exact").limit(1).execute()
        print(f"✅ 成功! 目前向量數據量: {chunk_res.count}")

        print("\n🏆 檢查完畢：資料庫連線正常！")

    except Exception as e:
        print(f"\n❌ 資料庫異常: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
