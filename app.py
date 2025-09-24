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
    "自定義...": "Custom", "1024x1024": "正方形 (1:1) - 通用", "1080x1080": "IG 貼文 (1:1)",
    "1080x1350": "IG 縱向 (4:5)", "1080x1920": "IG Story (9:16)", "1200x630": "FB 橫向 (1.91:1)",
}

def rerun_app():
    if hasattr(st, 'rerun'): st.rerun()
    elif hasattr(st, 'experimental_rerun'): st.experimental_rerun()
    else: st.stop()

st.set_page_config(page_title="FLUX AI - 多供應商整合版", page_icon="⚓", layout="wide")

# API 提供商，新增 NavyAI
API_PROVIDERS = {
    "NavyAI": {"name": "NavyAI", "base_url_default": "https://api.navy/v1", "key_prefix": "sk-", "description": "統一接入多種現代 AI 模型", "icon": "⚓"},
    "Krea AI Studio": {"name": "Krea AI Studio", "base_url_default": "https://api.krea.ai/v1", "key_prefix": "krea-", "description": "專業美學圖像生成平台", "icon": "🎨"},
    "Pollinations.ai": {"name": "Pollinations.ai", "base_url_default": "https://image.pollinations.ai", "key_prefix": "", "description": "支援免費和認證模式的 API", "icon": "🌸"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "key_prefix": "sk-", "description": "OpenAI 官方或兼容 API", "icon": "🤖"},
}

# --- 核心函數 (大部分與之前版本相同，為簡潔省略) ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {
            "預設 NavyAI": {'provider': 'NavyAI', 'api_key': '', 'base_url': 'https://api.navy/v1', 'validated': False}
        }
    if 'active_profile_name' not in st.session_state or st.session_state.active_profile_name not in st.session_state.api_profiles:
        st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
    defaults = {'generation_history': [], 'favorite_images': [], 'discovered_models': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    try:
        if provider == "Pollinations.ai": return (True, "Pollinations.ai 已就緒") if requests.get(f"{base_url}/models", timeout=10).ok else (False, "連接失敗")
        else: OpenAI(api_key=api_key, base_url=base_url).models.list(); return True, "API 密鑰驗證成功"
    except Exception as e: return False, f"API 驗證失敗: {e}"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    # ... (此處的生成邏輯會根據提供商調用不同的參數) ...
    try:
        return True, client.images.generate(**params)
    except Exception as e:
        return False, str(e)


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
        sel_prov = st.selectbox("API 提供商", provs, index=provs.index(active_config.get('provider', 'NavyAI')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
        
        # ... (此處的 UI 邏輯與之前相同，為簡潔省略) ...
        api_key_input = ''
        if sel_prov != "Pollinations.ai":
            api_key_input = st.text_input("API 密鑰", value=active_config.get('api_key', ''), type="password")
        
        base_url_input = st.text_input("API 端點 URL", value=active_config.get('base_url', API_PROVIDERS[sel_prov]['base_url_default']))

    st.markdown("---")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.active_profile_name)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存/更新存檔", type="primary"):
            # ... (保存邏輯與之前相同) ...
            pass
    with col2:
        if st.button("🗑️ 刪除此存檔", disabled=len(st.session_state.api_profiles) <= 1):
            # ... (刪除邏輯與之前相同) ...
            pass

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
        # ...
    else:
        st.error(f"🔴 '{st.session_state.active_profile_name}' 未驗證")
    st.markdown("---")
    st.info(f"⚡ **免費版優化**\n- 歷史: {MAX_HISTORY_ITEMS}\n- 收藏: {MAX_FAVORITE_ITEMS}")

st.title("⚓ FLUX AI - 多供應商整合版")

# --- 主介面 ---
tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史記錄", f"⭐ 收藏夾"])

with tab1:
    if not api_configured: st.warning("⚠️ 請在側邊欄選擇一個已驗證的存檔。")
    else:
        # ... (模型選擇、風格預設、提示詞等 UI 與之前相同) ...
        sel_model = st.selectbox("模型:", ["flux.1-schnell"]) # 假設的模型
        selected_style = st.selectbox("🎨 風格預設:", list(STYLE_PRESETS.keys()))
        prompt_val = st.text_area("✍️ 提示詞:", height=100, placeholder="一隻貓在日落下飛翔，電影感")
        negative_prompt_val = st.text_area("🚫 負向提示詞:", height=50, placeholder="模糊, 糟糕的解剖結構")

        size_preset = st.selectbox("圖像尺寸", options=list(IMAGE_SIZES.keys()), format_func=lambda x: IMAGE_SIZES[x])
        # ... (自定義尺寸邏輯與之前相同) ...
        width, height = 1024, 1024
        if size_preset == "自定義...":
            col_w, col_h = st.columns(2)
            with col_w: width = st.slider("寬度 (px)", 512, 2048, 1024, 64)
            with col_h: height = st.slider("高度 (px)", 512, 2048, 1024, 64)
            final_size_str = f"{width}x{height}"
        else:
            final_size_str = size_preset

        if st.button("🚀 生成圖像", type="primary", use_container_width=True, disabled=not prompt_val.strip()):
            final_prompt = f"{prompt_val}, {STYLE_PRESETS[selected_style]}" if selected_style != "無" else prompt_val
            with st.spinner(f"🎨 正在生成圖像..."):
                params = {"model": sel_model, "prompt": final_prompt, "negative_prompt": negative_prompt_val, "size": final_size_str}
                success, result = generate_images_with_retry(client, **params)
                if success:
                    # ... (顯示結果邏輯與之前相同) ...
                    st.success("✨ 圖像生成成功！")
                else: st.error(f"❌ 生成失敗: {result}")

# ... (歷史和收藏夾標籤的程式碼與之前相同) ...
with tab2: st.info("📭 尚無生成歷史。")
with tab3: st.info("⭐ 尚無收藏的圖像。")

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>⚓ 多供應商整合版 | 部署在 Koyeb 免費實例 ⚓</small></div>""", unsafe_allow_html=True)
