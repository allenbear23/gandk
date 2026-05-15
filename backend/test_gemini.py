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
            if 'generateContent' in m.supported_generation_methods:
                print(f"  - {m.name}")
        
        # 嘗試使用列表中的 gemini-flash-latest
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content("你好，請跟我說聲『測試成功』")
        
        print(f"✅ 連線成功！")
        print(f"🤖 AI 回應: {response.text}")
    except Exception as e:
        print(f"❌ 連線失敗：{str(e)}")

if __name__ == "__main__":
    test_gemini()
