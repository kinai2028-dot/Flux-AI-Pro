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
    "自定義...": "Custom",
    "1024x1024": "正方形 (1:1) - 通用", "1080x1080": "IG 貼文 (1:1)",
    "1080x1350": "IG 縱向 (4:5)", "1080x1920": "IG Story (9:16)",
    "1200x630": "FB 橫向 (1.91:1)", "1344x768": "寬螢幕 (16:9)",
}

def rerun_app():
    if hasattr(st, 'rerun'): st.rerun()
    elif hasattr(st, 'experimental_rerun'): st.experimental_rerun()
    else: st.stop()

st.set_page_config(page_title="FLUX Pollinations.ai Studio", page_icon="🌸", layout="wide")

# API 提供商
API_PROVIDERS = {
    "Pollinations.ai": {"name": "Pollinations.ai Studio", "base_url_default": "https://image.pollinations.ai", "key_prefix": "", "description": "專業美學圖像生成平台", "icon": "🌸"},
    "OpenAI Compatible": {"name": "OpenAI 兼容 API", "base_url_default": "https://api.openai.com/v1", "key_prefix": "sk-", "description": "OpenAI 官方或兼容 API", "icon": "🤖"},
    "Custom": {"name": "自定義 API", "base_url_default": "", "key_prefix": "", "description": "自定義的 API 端點", "icon": "🔧"},
}

BASE_FLUX_MODELS = {"flux": {"name": "FLUX (預設)", "description": "最新的穩定擴散模型", "icon": "⚡", "priority": 1}}

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

def get_active_config(): return st.session_state.api_profiles.get(st.session_state.active_profile_name, {})

def auto_discover_flux_models(client, provider: str, base_url: str) -> Dict[str, Dict]:
    discovered_models = {}
    try:
        if provider == "Pollinations.ai":
            response = requests.get(f"{base_url}/models", timeout=10)
            if response.ok:
                for model_name in response.json():
                    discovered_models[model_name] = {"name": model_name, "icon": "🌸"}
        else:
            for model in client.models.list().data:
                discovered_models[model.id] = {"name": model.id, "icon": "🤖"}
        return discovered_models
    except Exception as e:
        st.warning(f"模型發現失敗: {e}")
        return {}

def merge_models() -> Dict[str, Dict]: return {**BASE_FLUX_MODELS, **st.session_state.get('discovered_models', {})}

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    try:
        if provider == "Pollinations.ai": return (True, "Pollinations.ai 已就緒") if requests.get(f"{base_url}/models", timeout=10).ok else (False, "連接失敗")
        else: OpenAI(api_key=api_key, base_url=base_url).models.list(); return True, "API 密鑰驗證成功"
    except Exception as e: return False, f"API 驗證失敗: {e}"

def generate_images_with_retry(client, **params) -> Tuple[bool, any]:
    prompt = params.pop("prompt", "")
    if (neg_prompt := params.pop("negative_prompt", None)): prompt += f" --no {neg_prompt}"
    provider = get_active_config().get('provider')
    try:
        if provider == "Pollinations.ai":
            width, height = params.get("size", "1024x1024").split('x')
            api_params = {k: v for k, v in {"model": params.get("model"), "width": width, "height": height, "seed": random.randint(0, 1000000), "nologo": params.get("nologo"), "private": params.get("private"), "enhance": params.get("enhance"), "safe": params.get("safe")}.items() if v is not None}
            cfg = get_active_config()
            response = requests.get(f"{cfg['base_url']}/prompt/{quote(prompt)}?{urlencode(api_params)}", timeout=120)
            if response.ok: return True, type('MockResponse', (object,), {'data': [type('obj', (object,), {'url': f"data:image/png;base64,{base64.b64encode(response.content).decode()}"})()]})()
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        else:
            params["prompt"] = prompt
            return True, client.images.generate(**params)
    except Exception as e: return False, str(e)

def add_to_history(prompt: str, negative_prompt: str, model: str, images: List[str], metadata: Dict):
    history = st.session_state.generation_history
    history.insert(0, {"id": str(uuid.uuid4()), "timestamp": datetime.datetime.now(), "prompt": prompt, "negative_prompt": negative_prompt, "model": model, "images": images, "metadata": metadata})
    st.session_state.generation_history = history[:MAX_HISTORY_ITEMS]

def display_image_with_actions(image_url: str, image_id: str, history_item: Dict):
    # ... (此函數與之前版本相同，為簡潔省略) ...
    pass

def init_api_client():
    cfg = get_active_config()
    if cfg.get('provider') != "Pollinations.ai" and cfg.get('api_key'):
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def show_api_settings():
    # ... (此函數與之前版本相同，為簡潔省略) ...
    pass

init_session_state()
client = init_api_client()
cfg = get_active_config()
api_configured = cfg.get('validated', False)

# --- 側邊欄 ---
with st.sidebar:
    # ... (此處的 UI 邏輯與之前相同，為簡潔省略) ...
    st.info(f"⚡ **免費版優化**\n- 歷史: {MAX_HISTORY_ITEMS}\n- 收藏: {MAX_FAVORITE_ITEMS}")

st.title("🌸 FLUX Pollinations.ai Studio - 專業美學版")

# --- 主介面 ---
tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史", f"⭐ 收藏"])

with tab1:
    if not api_configured: st.warning("⚠️ 請在側邊欄選擇一個已驗證的存檔。")
    else:
        all_models = merge_models()
        if not all_models: st.warning("⚠️ 未發現模型，請點擊「發現模型」。")
        else:
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

            num_images = 1
            enhance, private, nologo, safe = False, False, False, False
            if cfg['provider'] == "Pollinations.ai":
                st.caption("Pollinations.ai 一次僅支持生成一張圖像。")
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
