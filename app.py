import streamlit as st
from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO
import datetime
import base64
from typing import Dict, List, Tuple
import time
import random
import json
import uuid
import os
import re
from urllib.parse import urlencode, quote
import gc

# 為免費方案設定限制
MAX_HISTORY_ITEMS = 15
MAX_FAVORITE_ITEMS = 30
MAX_BATCH_SIZE = 4

# 風格預設
STYLE_PRESETS = {
    "無": "", "電影感": "cinematic, dramatic lighting, high detail, sharp focus",
    "動漫風": "anime style, vibrant colors, clean line art", "賽博龐克": "cyberpunk, neon lights, futuristic city, high-tech",
    "水彩畫": "watercolor painting, soft wash, blended colors", "奇幻藝術": "fantasy art, epic, detailed, magical",
}

# 擴展的圖像尺寸選項
IMAGE_SIZES = {
    "自定義...": "Custom", "1024x1024": "正方形 (1:1)", "1080x1080": "IG 貼文 (1:1)",
    "1080x1350": "IG 縱向 (4:5)", "1080x1920": "IG Story (9:16)", "1200x630": "FB 橫向 (1.91:1)",
}

def rerun_app():
    if hasattr(st, 'rerun'): st.rerun()
    elif hasattr(st, 'experimental_rerun'): st.experimental_rerun()
    else: st.stop()

st.set_page_config(page_title="FLUX AI (最終優化版)", page_icon="🚀", layout="wide")

# API 提供商
API_PROVIDERS = {
    "Pollinations.ai": {"name": "Pollinations.ai Studio", "base_url_default": "https://image.pollinations.ai", "icon": "🌸"},
    "NavyAI": {"name": "NavyAI", "base_url_default": "https://api.navy/v1", "icon": "⚓"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "icon": "🤖"},
}

BASE_FLUX_MODELS = {"flux.1-schnell": {"name": "FLUX.1 Schnell", "icon": "⚡", "priority": 1}}

# --- 核心函數 ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {"預設 Pollinations": {'provider': 'Pollinations.ai', 'api_key': '', 'base_url': 'https://image.pollinations.ai', 'validated': True, 'pollinations_auth_mode': '免費', 'pollinations_token': '', 'pollinations_referrer': ''}}
    if 'active_profile_name' not in st.session_state or st.session_state.active_profile_name not in st.session_state.api_profiles:
        st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
    defaults = {'generation_history': [], 'favorite_images': [], 'discovered_models': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def auto_discover_models(client, provider, base_url) -> Dict[str, Dict]:
    # ... (此函數與之前版本相同)
    pass

def merge_models() -> Dict[str, Dict]:
    # ... (此函數與之前版本相同)
    pass

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    # ... (此函數與之前版本相同)
    pass

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    # ... (此函數與之前版本相同)
    pass

def add_to_history(prompt: str, negative_prompt: str, model: str, images: List[str], metadata: Dict):
    # ... (此函數與之前版本相同)
    pass

def display_image_with_actions(b64_json: str, image_id: str, history_item: Dict):
    # ... (此函數與之前版本相同)
    pass

def init_api_client():
    cfg = get_active_config()
    if cfg.get('api_key') and cfg.get('provider') != "Pollinations.ai":
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def provider_changed_callback():
    """當 API 提供商選擇框改變時，自動更新 URL 和清空密鑰。"""
    provider = st.session_state.provider_selectbox
    st.session_state.base_url_input = API_PROVIDERS[provider]['base_url_default']
    st.session_state.api_key_input = ""
    # 重置 Pollinations 特定設置
    st.session_state.pollinations_auth_mode = '免費'
    st.session_state.pollinations_referrer = ''
    st.session_state.pollinations_token = ''

def load_profile_to_edit_state(profile_name):
    """將選定的存檔加載到用於編輯的會話狀態中。"""
    config = st.session_state.api_profiles.get(profile_name, {})
    st.session_state.provider_selectbox = config.get('provider', 'Pollinations.ai')
    st.session_state.base_url_input = config.get('base_url', API_PROVIDERS[st.session_state.provider_selectbox]['base_url_default'])
    st.session_state.api_key_input = config.get('api_key', '')
    st.session_state.pollinations_auth_mode = config.get('pollinations_auth_mode', '免費')
    st.session_state.pollinations_referrer = config.get('pollinations_referrer', '')
    st.session_state.pollinations_token = config.get('pollinations_token', '')
    st.session_state.last_edited_profile = profile_name

def show_api_settings():
    st.subheader("⚙️ API 存檔管理")
    profile_names = list(st.session_state.api_profiles.keys())
    active_profile_name = st.selectbox("活動存檔", profile_names, index=profile_names.index(st.session_state.get('active_profile_name', profile_names[0])))

    if active_profile_name != st.session_state.get('active_profile_name'):
        st.session_state.active_profile_name = active_profile_name
        st.session_state.discovered_models = {}
        rerun_app()
    
    # 檢查是否需要重新加載編輯器的狀態
    if 'last_edited_profile' not in st.session_state or st.session_state.last_edited_profile != active_profile_name:
        load_profile_to_edit_state(active_profile_name)

    with st.expander("📝 編輯存檔內容", expanded=True):
        sel_prov_name = st.selectbox(
            "API 提供商", list(API_PROVIDERS.keys()), 
            key='provider_selectbox',
            format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}",
            on_change=provider_changed_callback
        )
        
        if sel_prov_name == "Pollinations.ai":
            st.radio("認證模式", ["免費", "域名", "令牌"], key='pollinations_auth_mode', horizontal=True)
            st.text_input("應用域名 (Referrer)", key='pollinations_referrer', placeholder="例如: my-app.koyeb.app", disabled=(st.session_state.pollinations_auth_mode != '域名'))
            st.text_input("API 令牌 (Token)", key='pollinations_token', type="password", disabled=(st.session_state.pollinations_auth_mode != '令牌'))
        else:
            st.text_input("API 密鑰", key='api_key_input', type="password")
        
        st.text_input("API 端點 URL", key='base_url_input')

    profile_name_input = st.text_input("存檔名稱", value=active_profile_name)
    if st.button("💾 保存/更新存檔", type="primary"):
        new_config = {
            'provider': st.session_state.provider_selectbox, 
            'api_key': st.session_state.api_key_input, 
            'base_url': st.session_state.base_url_input, 
            'pollinations_auth_mode': st.session_state.pollinations_auth_mode, 
            'pollinations_referrer': st.session_state.pollinations_referrer, 
            'pollinations_token': st.session_state.pollinations_token
        }
        is_valid, msg = validate_api_key(new_config['api_key'], new_config['base_url'], new_config['provider'])
        new_config['validated'] = is_valid
        
        if profile_name_input != active_profile_name and active_profile_name in st.session_state.api_profiles:
            del st.session_state.api_profiles[active_profile_name]

        st.session_state.api_profiles[profile_name_input] = new_config
        st.session_state.active_profile_name = profile_name_input
        st.session_state.discovered_models = {}
        st.success(f"存檔 '{profile_name_input}' 已保存。驗證: {'成功' if is_valid else '失敗'}")
        time.sleep(1); rerun_app()

# --- 主執行流程 ---
init_session_state()
client = init_api_client()
cfg = get_active_config()
api_configured = cfg.get('validated', False)

# --- 側邊欄 UI ---
with st.sidebar:
    show_api_settings()
    # ... (其餘側邊欄 UI 與之前版本相同)

st.title("🚀 FLUX AI (最終優化版)")

# --- 主介面 ---
# ... (主介面 UI 和生成邏輯與之前版本完全相同)

