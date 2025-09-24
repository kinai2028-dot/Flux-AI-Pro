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
        # 預設啟用列表中的第一個提供商
        st.session_state.active_provider_name = list(st.session_state.providers.keys())[0]
    if 'api_keys' not in st.session_state:
        # 為所有提供商初始化一個空的金鑰儲存字典
        st.session_state.api_keys = {name: "" for name in st.session_state.providers.keys()}
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []

# ==============================================================================
# 3. API 管理頁面函式 (統一 KEY 設定)
# ==============================================================================

def page_api_management():
    """一個獨立的頁面，用於新增、查看和管理所有 API 提供商及其金鑰。"""
    st.header("🔧 API 提供商管理")
    
    # --- 新增自定義 API 的表單 ---
    with st.expander("➕ 新增自定義 API 提供商"):
        with st.form("new_api_form", clear_on_submit=True):
            name = st.text_input("API 名稱")
            base_url = st.text_input("Base URL")
            key = st.text_input("API 金鑰", type="password")
            submitted = st.form_submit_button("💾 儲存")

            if submitted and name and base_url:
                st.session_state.providers[name] = {"name": name, "base_url": base_url, "icon": "⚙️"}
                # 同時初始化它的 key
                st.session_state.api_keys[name] = key if key else ""
                st.success(f"已成功新增 '{name}'！")
                st.rerun()

    st.markdown("---")

    # --- 顯示所有已配置的 API 提供商 (包含可編輯的 KEY 欄位) ---
    st.subheader("📋 已配置的 API 列表")
    
    if not st.session_state.providers:
        st.info("暫無任何 API 提供商。")
        return

    for name, info in st.session_state.providers.items():
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 3, 1.2])
            with col1:
                st.markdown(f"#### {info.get('icon', '')} {name}")
                st.caption(f"URL: {info['base_url']}")
            
            with col2:
                # 為所有提供商（包括預設的）加入可編輯的 API Key 輸入框
                current_key = st.session_state.api_keys.get(name, "")
                new_key = st.text_input(
                    "API 金鑰 (在此輸入或更新)",
                    value=current_key,
                    key=f"key_input_{name}",
                    type="password",
                    label_visibility="collapsed"
                )
                if new_key != current_key:
                    st.session_state.api_keys[name] = new_key
                    st.success(f"已更新 '{name}' 的 API 金鑰！")
                    st.rerun()

            with col3:
                # 啟用按鈕
                if st.session_state.active_provider_name == name:
                    st.button("✅ 目前使用", disabled=True, use_container_width=True)
                else:
                    if st.button("🚀 使用此 API", key=f"use_{name}", use_container_width=True):
                        st.session_state.active_provider_name = name
                        st.rerun()
                
                # 刪除按鈕 (僅對非預設提供商顯示)
                if name not in DEFAULT_PROVIDERS:
                    if st.button("🗑️ 刪除", key=f"del_{name}", type="secondary", use_container_width=True):
                        del st.session_state.providers[name]
                        del st.session_state.api_keys[name]
                        if st.session_state.active_provider_name == name:
                            st.session_state.active_provider_name = list(st.session_state.providers.keys())[0]
                        st.rerun()

# ==============================================================================
# 4. 主生成頁面與主應用流程 (與上一版相同)
# ==============================================================================
def page_image_generation():
    st.title("🎨 Flux AI 生成器")
    active_provider_name = st.session_state.active_provider_name
    active_provider_info = st.session_state.providers.get(active_provider_name, {})
    api_key = st.session_state.api_keys.get(active_provider_name)
    
    if not active_provider_info or not api_key:
        st.error(f"❌ '{active_provider_name}' 的 API 金鑰未設定。請前往「API 管理」頁面進行設定。")
        st.stop()
        
    st.caption(f"目前使用: {active_provider_info.get('icon', '')} {active_provider_name}")
    # ... 此處省略圖像生成的 UI 程式碼 ...
    st.info("圖像生成介面")

def main():
    init_session_state()
    with st.sidebar:
        st.header("導航")
        page = st.radio("選擇頁面", ["🚀 圖像生成", "🔧 API 管理"], label_visibility="collapsed")
    
    if page == "🚀 圖像生成":
        page_image_generation()
    elif page == "🔧 API 管理":
        page_api_management()

if __name__ == "__main__":
    main()
