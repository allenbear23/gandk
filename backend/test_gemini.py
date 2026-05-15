import google.generativeai as genai
import os
from dotenv import load_dotenv

# 讀取 .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def test_gemini():
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY 環境變數")
        return

    print(f"📡 正在測試 Gemini API (Key 前四位: {api_key[:4]}...)")
    try:
        genai.configure(api_key=api_key)
        
        print("📋 可用模型列表：")
        for m in genai.list_models():
            methods = m.supported_generation_methods
            if 'generateContent' in methods or 'embedContent' in methods:
                print(f"  - {m.name} (Methods: {methods})")
        
        print("\n🧪 測試向量化 (Embedding)...")
        try:
            embed_res = genai.embed_content(
                model="models/gemini-embedding-2",
                content="測試向量化",
                task_type="RETRIEVAL_DOCUMENT"
            )
            print(f"✅ 向量化成功！(gemini-embedding-2) 維度: {len(embed_res['embedding'])}")
        except Exception as ee:
            print(f"❌ 向量化失敗 (gemini-embedding-2): {ee}")

        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content("你好，請跟我說聲『測試成功』")
        
        print(f"✅ 連線成功！")
        print(f"🤖 AI 回應: {response.text}")
    except Exception as e:
        print(f"❌ 連線失敗：{str(e)}")

if __name__ == "__main__":
    test_gemini()
