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
        st.session_state.api_keys = {}
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []

# ==============================================================================
# 3. API 管理頁面函式 (KEY 設定更新)
# ==============================================================================

def page_api_management():
    """一個獨立的頁面，用於新增、查看和管理 API 提供商。"""
    st.header("🔧 API 提供商管理")
    
    # --- 新增自定義 API 的表單 ---
    with st.expander("➕ 新增自定義 API 提供商"):
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

    # --- 顯示所有已配置的 API 提供商 (包含可編輯的 KEY 欄位) ---
    st.subheader("📋 已配置的 API 列表")
    
    if not st.session_state.providers:
        st.info("暫無任何 API 提供商。請新增一個自定義 API。")
        return

    for name, info in st.session_state.providers.items():
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 3, 1.2])
            with col1:
                st.markdown(f"#### {info.get('icon', '')} {name}")
                st.caption(f"URL: {info['base_url']}")
            
            with col2:
                # 直接在列表中加入可編輯的 API Key 輸入框
                current_key = st.session_state.api_keys.get(name, "")
                new_key = st.text_input(
                    "API 金鑰 (在此輸入或更新)",
                    value=current_key,
                    key=f"key_input_{name}",
                    type="password",
                    label_visibility="collapsed"
                )
                # 如果使用者輸入了新的 KEY，則立即儲存
                if new_key and new_key != current_key:
                    st.session_state.api_keys[name] = new_key
                    st.success(f"已更新 '{name}' 的 API 金鑰！")
                    # 使用 rerun 確保介面狀態同步
                    st.rerun()

            with col3:
                # 設為當前使用
                if st.session_state.active_provider_name == name:
                    st.button("✅ 目前使用", disabled=True, use_container_width=True)
                else:
                    if st.button("🚀 使用此 API", key=f"use_{name}", use_container_width=True):
                        st.session_state.active_provider_name = name
                        st.rerun()
                
                # 刪除按鈕
                if name not in DEFAULT_PROVIDERS:
                    if st.button("🗑️ 刪除", key=f"del_{name}", type="secondary", use_container_width=True):
                        # ... (刪除邏輯與上一版相同) ...
                        st.rerun()

# ==============================================================================
# 4. 主生成頁面與主應用流程 (與上一版相同)
# ==============================================================================
def page_image_generation():
    # ... (此處程式碼與上一版相同)
    pass

def main():
    init_session_state()
    with st.sidebar:
        st.header("導航")
        page = st.radio("選擇頁面", ["🚀 圖像生成", "🔧 API 管理"], label_visibility="collapsed")
    
    if page == "🚀 圖像生成":
        page_image_generation() # 假設此函式已定義
    elif page == "🔧 API 管理":
        page_api_management()

if __name__ == "__main__":
    main()
