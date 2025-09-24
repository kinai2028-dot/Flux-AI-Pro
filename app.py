import streamlit as st
from openai import OpenAI
from typing import Dict

# ==============================================================================
# 1. 應用程式全域設定
# ==============================================================================

st.set_page_config(
    page_title="Flux AI (可自訂 API)",
    page_icon="⚙️",
    layout="wide"
)

# 預設的 API 提供商
DEFAULT_PROVIDERS = {
    "NavyAI": {
        "name": "NavyAI",
        "base_url": "https://api.navy/v1",
        "icon": "🚢"
    },
    "Pollinations.ai": {
        "name": "Pollinations.ai",
        "base_url": "https://pollinations.ai/v1",
        "icon": "🌸"
    }
}

# ==============================================================================
# 2. Session State 初始化
# ==============================================================================

def init_session_state():
    """初始化會話狀態"""
    if 'providers' not in st.session_state:
        st.session_state.providers = DEFAULT_PROVIDERS.copy()
    if 'active_provider_name' not in st.session_state:
        st.session_state.active_provider_name = "NavyAI"
    if 'api_keys' not in st.session_state:
        # 將 API 金鑰分開儲存，便於管理
        st.session_state.api_keys = {}
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []

# ==============================================================================
# 3. API 管理頁面函式
# ==============================================================================

def page_api_management():
    """一個獨立的頁面，用於新增、查看和管理 API 提供商。"""
    st.header("🔧 API 提供商管理")
    
    # --- 新增自定義 API 的表單 ---
    with st.expander("➕ 新增自定義 API 提供商", expanded=False):
        with st.form("new_api_form", clear_on_submit=True):
            name = st.text_input("API 名稱 (例如：My Local AI)")
            base_url = st.text_input("Base URL (例如：http://localhost:8080/v1)")
            key = st.text_input("API 金鑰", type="password")
            submitted = st.form_submit_button("💾 儲存")

            if submitted and name and base_url and key:
                st.session_state.providers[name] = {"name": name, "base_url": base_url, "icon": "⚙️"}
                st.session_state.api_keys[name] = key
                st.success(f"已成功新增並儲存 '{name}'！")
                st.rerun()

    st.markdown("---")

    # --- 顯示所有已配置的 API 提供商 ---
    st.subheader("📋 已配置的 API 列表")
    
    if not st.session_state.providers:
        st.info("暫無任何 API 提供商。請新增一個自定義 API。")
        return

    for name, info in st.session_state.providers.items():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"#### {info.get('icon', '')} {name}")
                st.text_input("Base URL", value=info["base_url"], key=f"url_{name}", disabled=True)
            
            with col2:
                st.write("") # 增加間距
                # 設為當前使用
                if st.session_state.active_provider_name == name:
                    st.button("✅ 目前使用", key=f"use_{name}", disabled=True, use_container_width=True)
                else:
                    if st.button("🚀 使用此 API", key=f"use_{name}", use_container_width=True):
                        st.session_state.active_provider_name = name
                        st.rerun()
                
                # 刪除按鈕（僅對非預設提供商顯示）
                if name not in DEFAULT_PROVIDERS:
                    if st.button("🗑️ 刪除", key=f"del_{name}", type="secondary", use_container_width=True):
                        del st.session_state.providers[name]
                        if name in st.session_state.api_keys:
                            del st.session_state.api_keys[name]
                        # 如果刪除的是當前使用的，則切換回第一個
                        if st.session_state.active_provider_name == name:
                            st.session_state.active_provider_name = list(st.session_state.providers.keys())[0]
                        st.rerun()

# ==============================================================================
# 4. 主生成頁面函式
# ==============================================================================

def page_image_generation():
    """主圖像生成頁面。"""
    st.title("🎨 Flux AI 生成器")
    
    active_provider_name = st.session_state.active_provider_name
    active_provider_info = st.session_state.providers.get(active_provider_name, {})
    api_key = st.session_state.api_keys.get(active_provider_name)

    if not active_provider_info or not api_key:
        st.error(f"❌ '{active_provider_name}' 的 API 金鑰未設定。請前往「API 管理」頁面進行設定。")
        st.stop()
    
    # 顯示當前使用的 API
    st.caption(f"目前使用: {active_provider_info.get('icon', '')} {active_provider_name}")

    try:
        client = OpenAI(api_key=api_key, base_url=active_provider_info["base_url"])
    except Exception as e:
        st.error(f"無法初始化 API 客戶端: {e}")
        st.stop()

    # ... 此處省略圖像生成的 UI 程式碼（與上一版相同）...
    # 例如：選擇模型、輸入提示詞、調整參數、生成按鈕、顯示結果等
    st.info("圖像生成介面（此處為示意，實際程式碼與前一版相同）")

# ==============================================================================
# 5. 主應用程式流程
# ==============================================================================

def main():
    init_session_state()

    # 使用側邊欄作為頁面導航
    with st.sidebar:
        st.header("導航")
        page = st.radio(
            "選擇頁面",
            ["🚀 圖像生成", "🔧 API 管理"],
            label_visibility="collapsed"
        )
    
    if page == "🚀 圖像生成":
        page_image_generation()
    elif page == "🔧 API 管理":
        page_api_management()

if __name__ == "__main__":
    main()
