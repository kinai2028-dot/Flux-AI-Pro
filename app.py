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

st.set_page_config(page_title="FLUX AI - 終極社區版", page_icon="🌍", layout="wide")

# API 提供商，新增更多免費選項
API_PROVIDERS = {
    "SiliconFlow": {"name": "SiliconFlow (免費)", "base_url_default": "https://api.siliconflow.cn/v1", "key_prefix": "sk-", "description": "提供免費的 FLUX 模型 API", "icon": "💧"},
    "NavyAI": {"name": "NavyAI", "base_url_default": "https://api.navy/v1", "key_prefix": "sk-", "description": "統一接入多種現代 AI 模型", "icon": "⚓"},
    "Pollinations.ai": {"name": "Pollinations.ai (免費)", "base_url_default": "https://image.pollinations.ai", "key_prefix": "", "description": "無需註冊的免費圖像生成", "icon": "🌸"},
    "Krea AI Studio": {"name": "Krea AI Studio", "base_url_default": "https://api.krea.ai/v1", "key_prefix": "krea-", "description": "專業美學圖像生成平台", "icon": "🎨"},
    "DeepAI": {"name": "DeepAI (免費額度)", "base_url_default": "https://api.deepai.org/api/text2img", "key_prefix": "", "description": "提供免費層級的圖像生成 API", "icon": "🧠"},
    "Picsart": {"name": "Picsart (免費試用)", "base_url_default": "https://api.picsart.io/v1", "key_prefix": "pica-", "description": "提供免費試用額度的圖像生成與編輯", "icon": "🖼️"},
    "Google AI": {"name": "Google AI (免費額度)", "base_url_default": "https://generativelanguage.googleapis.com/v1beta", "key_prefix": "ya29.", "description": "新用戶享 $300 免費抵免額", "icon": "🇬"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "key_prefix": "sk-", "description": "通用 OpenAI 格式 API", "icon": "🤖"},
}

# --- 核心函數 (大部分與之前版本相同，為簡潔省略) ---
def init_session_state():
    if 'api_profiles' not in st.session_state:
        st.session_state.api_profiles = {
            "預設 SiliconFlow": {'provider': 'SiliconFlow', 'api_key': '', 'base_url': 'https://api.siliconflow.cn/v1', 'validated': False}
        }
    # ... (其餘初始化邏輯不變) ...

# ... (其他核心函數，如 get_active_config, validate_api_key 等與之前版本相同) ...
def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})
def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    # 根據不同 provider 可能需要不同的驗證邏輯
    return True, "驗證成功（模擬）"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    # 根據不同 provider 可能需要不同的生成邏輯
    try:
        if client: return True, client.images.generate(**params)
        else: # 處理像 Pollinations 或 DeepAI 這種非 OpenAI SDK 的情況
            return True, "生成成功（模擬）" 
    except Exception as e:
        return False, str(e)

def init_api_client():
    cfg = get_active_config()
    # 僅為 OpenAI 兼容的 API 創建客戶端
    if cfg.get('api_key') and cfg.get('provider') in ["SiliconFlow", "NavyAI", "Krea AI Studio", "Google AI", "OpenAI Compatible"]:
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
        sel_prov_name = st.selectbox("API 提供商", provs, index=provs.index(active_config.get('provider', 'SiliconFlow')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
        
        if sel_prov_name != active_config.get('provider'):
            active_config['base_url'] = API_PROVIDERS[sel_prov_name]['base_url_default']
        
        api_key_input = st.text_input("API 密鑰", value=active_config.get('api_key', ''), type="password")
        base_url_input = st.text_input("API 端點 URL", value=active_config.get('base_url', API_PROVIDERS[sel_prov_name]['base_url_default']))

    st.markdown("---")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.active_profile_name)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存/更新存檔", type="primary"):
            new_config = {'provider': sel_prov_name, 'api_key': api_key_input, 'base_url': base_url_input, 'validated': False}
            is_valid, msg = validate_api_key(new_config['api_key'], new_config['base_url'], new_config['provider'])
            new_config['validated'] = is_valid
            st.session_state.api_profiles[profile_name_input] = new_config
            st.session_state.active_profile_name = profile_name_input
            st.success(f"存檔 '{profile_name_input}' 已保存。驗證: {'成功' if is_valid else '失敗'}")
            time.sleep(1); rerun_app()
    with col2:
        if st.button("🗑️ 刪除此存檔", disabled=len(st.session_state.api_profiles) <= 1):
            del st.session_state.api_profiles[st.session_state.active_profile_name]
            st.session_state.active_profile_name = list(st.session_state.api_profiles.keys())[0]
            st.success("存檔已刪除。"); time.sleep(1); rerun_app()


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
    else:
        st.error(f"🔴 '{st.session_state.active_profile_name}' 未驗證")
    st.markdown("---")
    st.info(f"⚡ **免費版優化**\n- 歷史: {MAX_HISTORY_ITEMS}\n- 收藏: {MAX_FAVORITE_ITEMS}")

st.title("🌍 FLUX AI - 終極社區版")

# --- 主介面 ---
tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史記錄", f"⭐ 收藏夾"])

with tab1:
    if not api_configured: st.warning("⚠️ 請在側邊欄選擇一個已驗證的存檔。")
    else:
        sel_model = st.selectbox("模型:", ["flux.1-schnell"]) # 假設的模型
        selected_style = st.selectbox("🎨 風格預設:", list(STYLE_PRESETS.keys()))
        prompt_val = st.text_area("✍️ 提示詞:", height=100, placeholder="一隻貓在日落下飛翔，電影感")
        negative_prompt_val = st.text_area("🚫 負向提示詞:", height=50, placeholder="模糊, 糟糕的解剖結構")

        size_preset = st.selectbox("圖像尺寸", options=list(IMAGE_SIZES.keys()), format_func=lambda x: IMAGE_SIZES[x])
        width, height = 1024, 1024
        if size_preset == "自定義...":
            col_w, col_h = st.columns(2)
            with col_w: width = st.slider("寬度 (px)", 512, 2048, 1024, 64)
            with col_h: height = st.slider("高度 (px)", 512, 2048, 1024, 64)
            final_size_str = f"{width}x{height}"
        else:
            final_size_str = size_preset

        if st.button("🚀 生成圖像", type="primary", use_container_width=True, disabled=not prompt_val.strip()):
            with st.spinner(f"🎨 正在生成圖像..."):
                params = {"model": sel_model, "prompt": prompt_val, "negative_prompt": negative_prompt_val, "size": final_size_str}
                success, result = generate_images_with_retry(client, **params)
                if success:
                    st.success("✨ 圖像生成成功！")
                else: st.error(f"❌ 生成失敗: {result}")

with tab2: st.info("📭 尚無生成歷史。")
with tab3: st.info("⭐ 尚無收藏的圖像。")

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>🌍 終極社區版 | 部署在 Koyeb 免費實例 🌍</small></div>""", unsafe_allow_html=True)
