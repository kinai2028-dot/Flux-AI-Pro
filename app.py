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

def rerun_app():
    if hasattr(st, 'rerun'): st.rerun()
    elif hasattr(st, 'experimental_rerun'): st.experimental_rerun()
    else: st.stop()

st.set_page_config(page_title="Flux AI (存檔管理版)", page_icon="💾", layout="wide")

# --- API 和模型配置 ---
API_PROVIDERS = {"OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "key_prefix": "sk-", "description": "OpenAI 官方或兼容的 API 服務", "icon": "🤖"},"Navy": {"name": "Navy API", "base_url_default": "https://api.navy/v1", "key_prefix": "sk-", "description": "Navy 提供的 AI 圖像生成服務", "icon": "⚓"},"Pollinations.ai": {"name": "Pollinations.ai", "base_url_default": "https://image.pollinations.ai", "key_prefix": "", "description": "支援免費和認證模式的圖像生成 API", "icon": "🌸"},"Custom": {"name": "自定義 API", "base_url_default": "", "key_prefix": "", "description": "自定義的 API 端點", "icon": "🔧"}}
BASE_FLUX_MODELS = {"flux.1-schnell": {"name": "FLUX.1 Schnell", "description": "最快的生成速度", "icon": "⚡", "priority": 1},"flux.1-dev": {"name": "FLUX.1 Dev", "description": "開發版本", "icon": "🔧", "priority": 2}}
FLUX_MODEL_PATTERNS = {r'flux[\\.\\-]?1[\\.\\-]?schnell': {"name_template": "FLUX.1 Schnell", "icon": "⚡", "priority_base": 100},r'flux[\\.\\-]?1[\\.\\-]?dev': {"name_template": "FLUX.1 Dev", "icon": "🔧", "priority_base": 200},r'flux[\\.\\-]?1[\\.\\-]?pro': {"name_template": "FLUX.1 Pro", "icon": "👑", "priority_base": 300},r'flux[\\.\\-]?1[\\.\\-]?kontext|kontext': {"name_template": "FLUX.1 Kontext", "icon": "🎯", "priority_base": 400}}

# --- 核心函數 ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {
            "預設 Pollinations": {'provider': 'Pollinations.ai', 'api_key': '', 'base_url': 'https://image.pollinations.ai', 'validated': False, 'pollinations_auth_mode': '免費', 'pollinations_token': '', 'pollinations_referrer': ''}
        }
    if 'active_profile_name' not in st.session_state or st.session_state.active_profile_name not in st.session_state.api_profiles:
        st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
    
    defaults = {'generation_history': [], 'favorite_images': [], 'discovered_models': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def get_active_config():
    return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def auto_discover_flux_models(client, provider: str, base_url: str) -> Dict[str, Dict]:
    # ... (此函數與之前版本相同，為簡潔省略) ...
    return {} # 佔位

def analyze_model_name(model_id: str) -> Dict:
    # ... (此函數與之前版本相同，為簡潔省略) ...
    return {} # 佔位

def merge_models() -> Dict[str, Dict]:
    merged_models = {**BASE_FLUX_MODELS, **st.session_state.get('discovered_models', {})}
    return dict(sorted(merged_models.items(), key=lambda item: item[1].get('priority', 999)))

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    try:
        if provider == "Pollinations.ai": return (True, "Pollinations.ai 已就緒") if requests.get(f"{base_url}/models", timeout=10).ok else (False, "連接失敗")
        else:
            OpenAI(api_key=api_key, base_url=base_url).models.list()
            return True, "API 密鑰驗證成功"
    except Exception as e: return False, f"API 驗證失敗: {e}"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    # ... (此函數與之前版本相同，為簡潔省略) ...
    return False, "生成失敗" # 佔位

def add_to_history(prompt: str, negative_prompt: str, model: str, images: List[str], metadata: Dict):
    history = st.session_state.generation_history
    history.insert(0, {"id": str(uuid.uuid4()), "timestamp": datetime.datetime.now(), "prompt": prompt, "negative_prompt": negative_prompt, "model": model, "images": images, "metadata": metadata})
    st.session_state.generation_history = history[:MAX_HISTORY_ITEMS]

def display_image_with_actions(image_url: str, image_id: str, history_item: Dict):
    # ... (此函數與之前版本相同，為簡潔省略) ...
    pass # 佔位

def init_api_client():
    cfg = get_active_config()
    if cfg.get('provider') != "Pollinations.ai" and cfg.get('api_key'):
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def show_api_settings():
    st.subheader("⚙️ API 存檔管理")
    profile_names = list(st.session_state.api_profiles.keys())
    
    # 選擇活動存檔
    st.session_state.active_profile_name = st.selectbox("活動存檔", profile_names, index=profile_names.index(st.session_state.active_profile_name) if st.session_state.active_profile_name in profile_names else 0)
    
    active_config = get_active_config().copy() # 使用副本進行編輯

    st.markdown("---")
    st.markdown("##### 📝 編輯存檔內容")
    
    # API 提供商
    provs = list(API_PROVIDERS.keys())
    sel_prov = st.selectbox("API 提供商", provs, index=provs.index(active_config.get('provider', 'Pollinations.ai')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
    
    # 根據選擇的提供商顯示不同選項
    if sel_prov == "Pollinations.ai":
        st.markdown("###### 🌸 Pollinations.ai 認證")
        auth_mode = st.radio("模式", ["免費", "域名", "令牌"], horizontal=True, index=["免費", "域名", "令牌"].index(active_config.get('pollinations_auth_mode', '免費')))
        if auth_mode == "域名":
            referrer = st.text_input("應用域名", value=active_config.get('pollinations_referrer', ''), placeholder="例如: myapp.koyeb.app")
        elif auth_mode == "令牌":
            token = st.text_input("API 令牌", value=active_config.get('pollinations_token', ''), type="password")
        api_key_input = active_config.get('api_key', '')
    else:
        api_key_input = st.text_input("API 密鑰", value=active_config.get('api_key', ''), type="password")

    base_url_input = st.text_input("API 端點 URL", value=active_config.get('base_url', API_PROVIDERS[sel_prov]['base_url_default']))

    st.markdown("---")
    st.markdown("##### 💾 保存與操作")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.active_profile_name)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存/更新存檔", type="primary"):
            if not profile_name_input.strip():
                st.error("存檔名稱不能為空")
            else:
                new_config = {'provider': sel_prov, 'api_key': api_key_input, 'base_url': base_url_input, 'validated': False}
                if sel_prov == "Pollinations.ai":
                    new_config.update({'pollinations_auth_mode': auth_mode, 'pollinations_referrer': referrer if auth_mode == '域名' else '', 'pollinations_token': token if auth_mode == '令牌' else ''})
                
                with st.spinner("正在驗證並保存..."):
                    is_valid, msg = validate_api_key(new_config['api_key'], new_config['base_url'], new_config['provider'])
                    new_config['validated'] = is_valid
                    st.session_state.api_profiles[profile_name_input] = new_config
                    st.session_state.active_profile_name = profile_name_input
                    
                    if is_valid: st.success(f"✅ 存檔 '{profile_name_input}' 已保存並驗證。")
                    else: st.error(f"❌ 存檔已保存，但驗證失敗: {msg}")
                    time.sleep(1); rerun_app()
    with col2:
        if st.button("🗑️ 刪除此存檔", disabled=len(st.session_state.api_profiles) <= 1):
            del st.session_state.api_profiles[st.session_state.active_profile_name]
            st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
            st.success("存檔已刪除。")
            time.sleep(1); rerun_app()

init_session_state()
client = init_api_client()
cfg = get_active_config()
api_configured = cfg.get('validated', False)

# --- 側邊欄 ---
with st.sidebar:
    show_api_settings()
    st.markdown("---")
    if api_configured:
        st.success(f"🟢 活動存檔: '{st.session_state.active_profile_name}'")
        if st.button("🔍 發現模型", use_container_width=True):
            # ... (發現模型邏輯不變) ...
            pass
    else:
        st.error(f"🔴 '{st.session_state.active_profile_name}' 未配置或驗證")
    st.markdown("---")
    st.info(f"⚡ **免費版優化**\n- 歷史記錄: {MAX_HISTORY_ITEMS}\n- 收藏夾: {MAX_FAVORITE_ITEMS}")

st.title("💾 Flux AI (API 存檔管理版)")

# --- 主介面與其他標籤 (與之前版本基本相同，為簡潔省略) ---
st.info("主應用程式介面與之前版本相同，現在所有操作都將使用您在側邊欄選擇的活動 API 存檔。")
