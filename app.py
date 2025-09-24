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

st.set_page_config(page_title="FLUX Pollinations.ai Studio", page_icon="🌸", layout="wide")

# API 提供商
API_PROVIDERS = {
    "Pollinations.ai": {"name": "Pollinations.ai Studio", "base_url_default": "https://image.pollinations.ai", "key_prefix": "", "description": "深度整合的專業美學平台", "icon": "🌸"},
    "NavyAI": {"name": "NavyAI", "base_url_default": "https://api.navy/v1", "key_prefix": "sk-", "description": "統一接入多種現代 AI 模型", "icon": "⚓"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "key_prefix": "sk-", "description": "通用 OpenAI 格式 API", "icon": "🤖"},
}

# --- 核心函數 (大部分與之前版本相同) ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {
            "預設 Pollinations": {'provider': 'Pollinations.ai', 'api_key': '', 'base_url': 'https://image.pollinations.ai', 'validated': True, 'pollinations_auth_mode': '免費', 'pollinations_token': '', 'pollinations_referrer': ''}
        }
    if 'active_profile_name' not in st.session_state or st.session_state.active_profile_name not in st.session_state.api_profiles:
        st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
    defaults = {'generation_history': [], 'favorite_images': [], 'discovered_models': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    # ... (驗證邏輯不變) ...
    return True, "驗證成功（模擬）"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    prompt = params.pop("prompt", "")
    if (neg_prompt := params.pop("negative_prompt", None)): prompt += f" --no {neg_prompt}"
    provider = get_active_config().get('provider')
    try:
        if provider == "Pollinations.ai":
            width, height = params.get("size", "1024x1024").split('x')
            api_params = {k: v for k, v in {"model": params.get("model"), "width": width, "height": height, "seed": random.randint(0, 1000000), "nologo": params.get("nologo"), "private": params.get("private"), "enhance": params.get("enhance"), "safe": params.get("safe")}.items() if v is not None}
            cfg = get_active_config()
            headers = {}
            auth_mode = cfg.get('pollinations_auth_mode', '免費')
            if auth_mode == '令牌' and cfg.get('pollinations_token'): headers['Authorization'] = f"Bearer {cfg['pollinations_token']}"
            elif auth_mode == '域名' and cfg.get('pollinations_referrer'): headers['Referer'] = cfg['pollinations_referrer']
            
            response = requests.get(f"{cfg['base_url']}/prompt/{quote(prompt)}?{urlencode(api_params)}", headers=headers, timeout=120)
            if response.ok: return True, type('MockResponse', (object,), {'data': [type('obj', (object,), {'url': f"data:image/png;base64,{base64.b64encode(response.content).decode()}"})()]})()
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        else:
            params["prompt"] = prompt
            return True, client.images.generate(**params)
    except Exception as e: return False, str(e)

def init_api_client():
    cfg = get_active_config()
    if cfg.get('api_key') and cfg.get('provider') != "Pollinations.ai":
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def show_api_settings():
    st.subheader("⚙️ API 存檔管理")
    profile_names = list(st.session_state.api_profiles.keys())
    st.session_state.active_profile_name = st.selectbox("活動存檔", profile_names, index=profile_names.index(st.session_state.active_profile_name) if st.session_state.active_profile_name in profile_names else 0)
    active_config = get_active_config().copy()
    
    with st.expander("📝 編輯存檔內容", expanded=True):
        provs = list(API_PROVIDERS.keys())
        sel_prov_name = st.selectbox("API 提供商", provs, index=provs.index(active_config.get('provider', 'Pollinations.ai')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
        
        # Pollinations.ai 專用認證 UI
        if sel_prov_name == "Pollinations.ai":
            auth_mode = st.radio("認證模式", ["免費", "域名", "令牌"], horizontal=True, index=["免費", "域名", "令牌"].index(active_config.get('pollinations_auth_mode', '免費')))
            referrer = st.text_input("應用域名 (Referrer)", value=active_config.get('pollinations_referrer', ''), placeholder="例如: my-app.koyeb.app", disabled=(auth_mode != '域名'))
            token = st.text_input("API 令牌 (Token)", value=active_config.get('pollinations_token', ''), type="password", disabled=(auth_mode != '令牌'))
            api_key_input = '' # Pollinations.ai 不使用傳統 API Key
        else:
            api_key_input = st.text_input("API 密鑰", value=active_config.get('api_key', ''), type="password")
            auth_mode, referrer, token = '免費', '', '' # 重置 Pollinations 參數
        
        base_url_input = st.text_input("API 端點 URL", value=active_config.get('base_url', API_PROVIDERS[sel_prov_name]['base_url_default']))

    st.markdown("---")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.active_profile_name)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存/更新存檔", type="primary"):
            new_config = {'provider': sel_prov_name, 'api_key': api_key_input, 'base_url': base_url_input, 'validated': False, 'pollinations_auth_mode': auth_mode, 'pollinations_referrer': referrer, 'pollinations_token': token}
            is_valid, msg = validate_api_key(new_config['api_key'], new_config['base_url'], new_config['provider'])
            new_config['validated'] = is_valid
            st.session_state.api_profiles[profile_name_input] = new_config
            st.session_state.active_profile_name = profile_name_input
            st.success(f"存檔 '{profile_name_input}' 已保存。")
            time.sleep(1); rerun_app()
    # ... (刪除按鈕邏輯不變) ...

init_session_state()
client = init_api_client()
cfg = get_active_config()
api_configured = cfg.get('validated', False)

# --- 側邊欄 ---
with st.sidebar:
    show_api_settings()
    # ... (其餘側邊欄邏輯不變) ...

st.title("🌸 FLUX Pollinations.ai Studio - 專業美學版")

# --- 主介面 ---
tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史", f"⭐ 收藏"])

with tab1:
    if not api_configured: st.warning("⚠️ 請在側邊欄選擇一個已驗證的存檔。")
    else:
        all_models = {"flux": {"name": "FLUX (預設)", "icon": "⚡"}} # 簡化模型
        sel_model = st.selectbox("模型:", list(all_models.keys()), format_func=lambda x: f"{all_models[x].get('icon', '🤖')} {all_models[x].get('name', x)}")
        selected_style = st.selectbox("🎨 風格預設:", list(STYLE_PRESETS.keys()))
        prompt_val = st.text_area("✍️ 提示詞:", height=100)
        negative_prompt_val = st.text_area("🚫 負向提示詞:", height=50)
        
        size_preset = st.selectbox("圖像尺寸", options=list(IMAGE_SIZES.keys()), format_func=lambda x: IMAGE_SIZES[x])
        width, height = 1024, 1024
        if size_preset == "自定義...":
            col_w, col_h = st.columns(2)
            with col_w: width = st.slider("寬度 (px)", 512, 2048, 1024, 64)
            with col_h: height = st.slider("高度 (px)", 512, 2048, 1024, 64)
            final_size_str = f"{width}x{height}"
        else:
            final_size_str = size_preset

        # Pollinations.ai 專用進階選項
        enhance, private, nologo, safe = False, False, False, False
        if cfg.get('provider') == "Pollinations.ai":
            with st.expander("🌸 Pollinations.ai 進階選項"):
                enhance = st.checkbox("增強提示詞 (LLM)", value=True)
                private = st.checkbox("私密模式", value=True)
                nologo = st.checkbox("移除標誌", value=True)
                safe = st.checkbox("安全模式 (NSFW過濾)", value=False)
        
        if st.button("🚀 生成圖像", type="primary", use_container_width=True, disabled=not prompt_val.strip()):
            final_prompt = f"{prompt_val}, {STYLE_PRESETS[selected_style]}" if selected_style != "無" else prompt_val
            with st.spinner("🎨 正在生成圖像..."):
                params = {"model": sel_model, "prompt": final_prompt, "negative_prompt": negative_prompt_val, "size": final_size_str, "enhance": enhance, "private": private, "nologo": nologo, "safe": safe}
                success, result = generate_images_with_retry(client, **params)
                if success:
                    st.success("✨ 圖像生成成功！")
                    # ... (顯示結果邏輯) ...
                else: st.error(f"❌ 生成失敗: {result}")

with tab2: st.info("📭 尚無生成歷史。")
with tab3: st.info("⭐ 尚無收藏的圖像。")

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>🌸 專業美學版 | 部署在 Koyeb 免費實例 🌸</small></div>""", unsafe_allow_html=True)
