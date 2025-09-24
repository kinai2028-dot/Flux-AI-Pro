import streamlit as st
from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO
import datetime

# ==============================================================================
# 1. 應用程式全域設定 (更新版)
# ==============================================================================

st.set_page_config(
    page_title="Flux AI (NavyAI Discovery)",
    page_icon="🚢",
    layout="wide"
)

# 新增 NavyAI 作為一個獨立的 API 提供商
API_PROVIDERS = {
    "NavyAI": {
        "name": "NavyAI",
        "base_url_default": "https://api.navy/v1" # 根據您提供的資訊，假設 v1 是路徑
    },
    "Pollinations.ai": {
        "name": "Pollinations.ai",
        "base_url_default": "https://pollinations.ai/v1"
    },
    "OpenAI Compatible": {
        "name": "OpenAI Compatible API",
        "base_url_default": "https://api.openai.com/v1"
    },
    "Custom": {"name": "自定義 API", "base_url_default": ""}
}

# 靜態模型列表 (作為基礎選項)
STATIC_FLUX_MODELS = {
    "flux.1.1-pro": {"name": "Flux 1.1 Pro (本地預設)"},
    "flux.1-schnell": {"name": "Flux 1 Schnell (本地預設)"},
}

# ==============================================================================
# 2. 核心功能函式 (新增模型發現)
# ==============================================================================

@st.cache_data(ttl=3600) # 快取模型列表1小時
def discover_flux_models(_client: OpenAI) -> dict:
    """
    從 API 客戶端動態發現所有包含 'flux' 關鍵字的模型。
    使用 _client 參數名是為了讓 Streamlit 快取機制正常工作。
    """
    discovered_models = {}
    try:
        models_list = _client.models.list()
        for model in models_list.data:
            if "flux" in model.id.lower():
                # 為發現的模型創建一個標準化的描述
                discovered_models[model.id] = {
                    "name": f"{model.id} (自動發現)"
                }
    except Exception as e:
        # 如果發現失敗，不會讓應用崩潰，只會在控制台打印錯誤
        print(f"模型自動發現失敗: {e}")
    return discovered_models

def init_session_state():
    """初始化會話狀態"""
    # ... (此處程式碼與上一版相同，省略以保持簡潔)

def show_api_settings():
    """顯示 API 設置界面"""
    # ... (此處程式碼與上一版相同，省略以保持簡潔)

# ==============================================================================
# 3. 主應用程式執行流程 (整合自動發現)
# ==============================================================================

def main():
    init_session_state()

    with st.sidebar:
        show_api_settings()

    st.title("🚢 Flux AI 生成器 (NavyAI 自動發現版)")

    if not st.session_state.get("api_key") or not st.session_state.get("base_url"):
        st.error("❌ 請在側邊欄或 Koyeb 環境變數中設置您的後端 API 密鑰和 URL。")
        st.stop()
    
    try:
        client = OpenAI(api_key=st.session_state.api_key, base_url=st.session_state.base_url)
    except Exception as e:
        st.error(f"無法初始化 API 客戶端: {e}")
        st.stop()

    # --- 動態獲取並合併模型列表 ---
    with st.spinner("正在從後端 API 發現可用模型..."):
        discovered_models = discover_flux_models(client)

    # 合併靜態和動態發現的模型
    all_models = {**STATIC_FLUX_MODELS, **discovered_models}

    if not all_models:
        st.warning("未發現任何可用的 Flux 模型。請檢查您的 API 設置或後端服務。")
        st.stop()

    # --- 圖像生成介面 ---
    st.subheader("1. 選擇模型")
    # 預設選擇列表中的第一個模型
    model = st.selectbox(
        "選擇模型",
        options=list(all_models.keys()),
        format_func=lambda x: all_models[x]['name'],
        label_visibility="collapsed"
    )
    
    st.subheader("2. 描述您的創意")
    prompt = st.text_area("在這裡輸入提示詞...", height=120, label_visibility="collapsed")

    st.subheader("3. 調整智能參數")
    # ... (參數設置區塊與上一版相同，省略)

    # --- 生成按鈕 ---
    st.subheader("4. 開始生成")
    if st.button("🚀 生成圖像", type="primary", disabled=not prompt, use_container_width=True):
        with st.spinner(f"正在向 {st.session_state.get('api_provider', '後端')} 發送請求..."):
            try:
                response = client.images.generate(model=model, prompt=prompt, n=1, size="1024x1024") # 假設 num_images 和 size 在參數區塊中定義
                st.success("🎉 圖像生成成功！")
                st.image(response.data[0].url, caption=f"模型: {model}")
                # ... (歷史記錄邏輯)
            except Exception as e:
                st.error(f"❌ 生成失敗: {e}")

if __name__ == "__main__":
    main()
