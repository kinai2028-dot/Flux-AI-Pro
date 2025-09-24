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

st.set_page_config(page_title="FLUX AI (終極自訂版)", page_icon="🛠️", layout="wide")

# API 提供商
API_PROVIDERS = {
    "SiliconFlow": {"name": "SiliconFlow (免費)", "base_url_default": "https://api.siliconflow.cn/v1", "icon": "💧"},
    "NavyAI": {"name": "NavyAI", "base_url_default": "https://api.navy/v1", "icon": "⚓"},
    "Pollinations.ai": {"name": "Pollinations.ai (免費)", "base_url_default": "https://image.pollinations.ai", "icon": "🌸"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "icon": "🤖"},
    "Custom": {"name": "自定義 API", "base_url_default": "", "icon": "🔧"},
}

# 基礎和動態發現的模型模式
BASE_FLUX_MODELS = {"flux.1-schnell": {"name": "FLUX.1 Schnell", "icon": "⚡", "priority": 1}}
FLUX_MODEL_PATTERNS = {
    r'flux[\.\-]?1[\.\-]?schnell': {"name": "FLUX.1 Schnell", "icon": "⚡", "priority": 100},
    r'flux[\.\-]?1[\.\-]?dev': {"name": "FLUX.1 Dev", "icon": "🔧", "priority": 200},
    r'flux[\.\-]?1[\.\-]?pro': {"name": "FLUX.1 Pro", "icon": "👑", "priority": 300},
}

# --- 核心函數 ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {"預設 SiliconFlow": {'provider': 'SiliconFlow', 'api_key': '', 'base_url': 'https://api.siliconflow.cn/v1', 'validated': False}}
    if 'active_profile_name' not in st.session_state or st.session_state.active_profile_name not in st.session_state.api_profiles:
        st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
    defaults = {'generation_history': [], 'favorite_images': [], 'discovered_models': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def analyze_model_name(model_id: str) -> Dict:
    model_lower = model_id.lower()
    for pattern, info in FLUX_MODEL_PATTERNS.items():
        if re.search(pattern, model_lower):
            return {"name": info["name"], "icon": info["icon"], "priority": info["priority"]}
    return {"name": model_id.replace('-', ' ').replace('_', ' ').title(), "icon": "🤖", "priority": 999}

def auto_discover_flux_models(client) -> Dict[str, Dict]:
    discovered_models = {}
    if not client: return {}
    try:
        models = client.models.list().data
        for model in models:
            if 'flux' in model.id.lower():
                model_info = analyze_model_name(model.id)
                discovered_models[model.id] = model_info
        return discovered_models
    except Exception as e:
        st.warning(f"自動發現模型失敗: {e}")
        return {}

def merge_models() -> Dict[str, Dict]:
    merged_models = {**BASE_FLUX_MODELS, **st.session_state.get('discovered_models', {})}
    return dict(sorted(merged_models.items(), key=lambda item: item[1].get('priority', 999)))

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    if provider == "Pollinations.ai": return True, "Pollinations.ai 無需驗證"
    try:
        OpenAI(api_key=api_key, base_url=base_url).models.list()
        return True, "API 密鑰驗證成功"
    except Exception as e: return False, f"API 驗證失敗: {e}"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    # ... (生成邏輯與之前版本相同) ...
    return True, "生成成功（模擬）"

def init_api_client():
    cfg = get_active_config()
    if cfg.get('api_key') and cfg.get('provider') != "Pollinations.ai":
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def show_api_settings():
    st.subheader("⚙️ API 存檔管理")
    profile_names = list(st.session_state.api_profiles.keys())
    
    # 使用 session state 來追蹤當前的選擇，以便比較
    if 'current_selectbox_provider' not in st.session_state:
        st.session_state.current_selectbox_provider = get_active_config().get('provider', 'SiliconFlow')

    sel_prov_name = st.selectbox(
        "API 提供商", list(API_PROVIDERS.keys()), 
        index=list(API_PROVIDERS.keys()).index(st.session_state.current_selectbox_provider), 
        format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}"
    )

    # 檢查提供商是否已更改
    if sel_prov_name != st.session_state.current_selectbox_provider:
        st.session_state.current_selectbox_provider = sel_prov_name
        # 清空舊的 key 和 URL，強制用戶輸入新的
        st.session_state.api_key_input = ""
        st.session_state.base_url_input = API_PROVIDERS[sel_prov_name]['base_url_default']
        rerun_app()

    # 從 session state 中獲取或初始化輸入值
    api_key_input = st.text_input("API 密鑰", value=st.session_state.get('api_key_input', ''), type="password", disabled=(sel_prov_name == "Pollinations.ai"))
    base_url_input = st.text_input("API 端點 URL", value=st.session_state.get('base_url_input', API_PROVIDERS[sel_prov_name]['base_url_default']))

    st.markdown("---")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.get('active_profile_name', '新存檔'))
    
    if st.button("💾 保存/更新存檔", type="primary"):
        new_config = {'provider': sel_prov_name, 'api_key': api_key_input, 'base_url': base_url_input}
        is_valid, msg = validate_api_key(new_config['api_key'], new_config['base_url'], new_config['provider'])
        new_config['validated'] = is_valid
        st.session_state.api_profiles[profile_name_input] = new_config
        st.session_state.active_profile_name = profile_name_input
        
        if is_valid:
            with st.spinner("驗證成功，正在自動發現模型..."):
                client = init_api_client()
                discovered = auto_discover_flux_models(client)
                st.session_state.discovered_models = discovered
                st.success(f"✅ 存檔 '{profile_name_input}' 已保存，並發現 {len(discovered)} 個 FLUX 模型！")
        else:
            st.error(f"❌ 存檔 '{profile_name_input}' 已保存，但驗證失敗: {msg}")
        
        time.sleep(2); rerun_app()

init_session_state()

# --- 側邊欄 ---
with st.sidebar:
    show_api_settings()
    # ... (其餘側邊欄 UI) ...

st.title("🛠️ FLUX AI (終極自訂版)")

# --- 主介面 ---
cfg = get_active_config()
api_configured = cfg.get('validated', False)
client = init_api_client()

tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史", f"⭐ 收藏"])

with tab1:
    if not api_configured: st.warning("⚠️ 請在側邊欄配置並驗證一個 API 存檔。")
    else:
        all_models = merge_models()
        if not all_models: st.warning("⚠️ 未發現任何 FLUX 模型。請檢查 API 配置或重新發現。")
        else:
            sel_model = st.selectbox("模型:", list(all_models.keys()), format_func=lambda x: f"{all_models.get(x, {}).get('icon', '🤖')} {all_models.get(x, {}).get('name', x)}")
            # ... (其餘生成 UI) ...
            if st.button("🚀 生成圖像", type="primary"):
                st.success("圖像生成成功！（模擬）")

# ... (歷史和收藏夾標籤) ...

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>🛠️ 終極自訂版 | 部署在 Koyeb 免費實例 🛠️</small></div>""", unsafe_allow_html=True)
