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

# 新增：擴展的圖像尺寸選項
IMAGE_SIZES = {
    "1024x1024": "正方形 (1:1) - 通用",
    "1080x1080": "IG 貼文 (1:1)",
    "1080x1350": "IG 縱向 (4:5)",
    "1080x1920": "IG Story (9:16)",
    "1200x630": "FB 橫向 (1.91:1)",
    "1344x768": "寬螢幕 (16:9)",
}

def rerun_app():
    if hasattr(st, 'rerun'): st.rerun()
    elif hasattr(st, 'experimental_rerun'): st.experimental_rerun()
    else: st.stop()

st.set_page_config(page_title="Flux AI (最終完善版)", page_icon="🌟", layout="wide")

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
    discovered_models = {}
    try:
        if provider == "Pollinations.ai":
            response = requests.get(f"{base_url}/models", timeout=10)
            if response.ok:
                for model_name in response.json():
                    model_info = analyze_model_name(model_name)
                    model_info.update({'source': 'pollinations', 'icon': '🌸'})
                    discovered_models[model_name] = model_info
        else:
            for model in client.models.list().data:
                if 'flux' in model.id.lower() or 'kontext' in model.id.lower():
                    model_info = analyze_model_name(model.id)
                    model_info['source'] = 'api_discovery'
                    discovered_models[model.id] = model_info
        return discovered_models
    except Exception as e:
        st.warning(f"模型發現失敗: {e}")
        return {}

def analyze_model_name(model_id: str) -> Dict:
    model_lower = model_id.lower()
    for pattern, info in FLUX_MODEL_PATTERNS.items():
        if re.search(pattern, model_lower):
            return {"name": info["name_template"], "icon": info["icon"], "description": f"自動發現的 {info['name_template']} 模型", "priority": info["priority_base"] + hash(model_id) % 100}
    return {"name": model_id.replace('-', ' ').replace('_', ' ').title(), "icon": "🤖", "description": f"自動發現的模型: {model_id}", "priority": 999}

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
    prompt = params.pop("prompt", "")
    if (neg_prompt := params.pop("negative_prompt", None)):
        prompt += f" --no {neg_prompt}"
    provider = get_active_config().get('provider')
    for attempt in range(3):
        try:
            if provider == "Pollinations.ai":
                width, height = params.get("size", "1024x1024").split('x')
                api_params = {k: v for k, v in {"model": params.get("model"), "width": width, "height": height, "seed": random.randint(0, 1000000), "nologo": params.get("nologo"), "private": params.get("private"), "enhance": params.get("enhance")}.items() if v is not None}
                headers, cfg = {}, get_active_config()
                auth_mode = cfg.get('pollinations_auth_mode', '免費')
                if auth_mode == '令牌' and cfg.get('pollinations_token'): headers['Authorization'] = f"Bearer {cfg['pollinations_token']}"
                elif auth_mode == '域名' and cfg.get('pollinations_referrer'): headers['Referer'] = cfg['pollinations_referrer']
                response = requests.get(f"{cfg['base_url']}/prompt/{quote(prompt)}?{urlencode(api_params)}", headers=headers, timeout=120)
                if response.ok: return True, type('MockResponse', (object,), {'data': [type('obj', (object,), {'url': f"data:image/png;base64,{base64.b64encode(response.content).decode()}"})()]})()
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            else:
                params["prompt"] = prompt
                return True, client.images.generate(**params)
        except Exception as e:
            if attempt < 2 and ("500" in str(e) or "timeout" in str(e).lower()): time.sleep((attempt + 1) * 2); continue
            return False, str(e)
    return False, "所有重試均失敗"

def add_to_history(prompt: str, negative_prompt: str, model: str, images: List[str], metadata: Dict):
    history = st.session_state.generation_history
    history.insert(0, {"id": str(uuid.uuid4()), "timestamp": datetime.datetime.now(), "prompt": prompt, "negative_prompt": negative_prompt, "model": model, "images": images, "metadata": metadata})
    st.session_state.generation_history = history[:MAX_HISTORY_ITEMS]

def display_image_with_actions(image_url: str, image_id: str, history_item: Dict):
    try:
        img_data = base64.b64decode(image_url.split(',')[1]) if image_url.startswith('data:image') else requests.get(image_url, timeout=10).content
        st.image(Image.open(BytesIO(img_data)), use_column_width=True)
        col1, col2, col3 = st.columns(3)
        with col1: st.download_button("📥 下載", img_data, f"flux_{image_id}.png", "image/png", key=f"dl_{image_id}", use_container_width=True)
        with col2:
            is_fav = any(fav['id'] == image_id for fav in st.session_state.favorite_images)
            if st.button("⭐" if is_fav else "☆", key=f"fav_{image_id}", use_container_width=True, help="收藏/取消收藏"):
                if is_fav: st.session_state.favorite_images = [f for f in st.session_state.favorite_images if f['id'] != image_id]
                elif len(st.session_state.favorite_images) < MAX_FAVORITE_ITEMS: st.session_state.favorite_images.append({"id": image_id, "image_url": image_url, "timestamp": datetime.datetime.now(), "history_item": history_item})
                else: st.warning(f"收藏夾已滿 (上限 {MAX_FAVORITE_ITEMS} 張)")
                rerun_app()
        with col3:
            if st.button("🎨 變體", key=f"vary_{image_id}", use_container_width=True, help="生成此圖像的變體"):
                st.session_state.update({'vary_prompt': history_item['prompt'], 'vary_negative_prompt': history_item.get('negative_prompt', ''), 'vary_model': history_item['model']})
                rerun_app()
    except Exception as e: st.error(f"圖像顯示錯誤: {e}")

def init_api_client():
    cfg = get_active_config()
    if cfg.get('provider') != "Pollinations.ai" and cfg.get('api_key'):
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
        sel_prov = st.selectbox("API 提供商", provs, index=provs.index(active_config.get('provider', 'Pollinations.ai')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
        referrer, token, api_key_input = '', '', active_config.get('api_key', '')
        auth_mode = active_config.get('pollinations_auth_mode', '免費')
        if sel_prov == "Pollinations.ai":
            auth_mode = st.radio("模式", ["免費", "域名", "令牌"], horizontal=True, index=["免費", "域名", "令牌"].index(auth_mode))
            if auth_mode == "域名": referrer = st.text_input("應用域名", value=active_config.get('pollinations_referrer', ''), placeholder="例如: myapp.koyeb.app")
            elif auth_mode == "令牌": token = st.text_input("API 令牌", value=active_config.get('pollinations_token', ''), type="password")
        else:
            api_key_input = st.text_input("API 密鑰", value=active_config.get('api_key', ''), type="password")
        base_url_input = st.text_input("API 端點 URL", value=active_config.get('base_url', API_PROVIDERS[sel_prov]['base_url_default']))
    st.markdown("---")
    profile_name_input = st.text_input("存檔名稱", value=st.session_state.active_profile_name)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存/更新存檔", type="primary"):
            if not profile_name_input.strip():
                st.error("存檔名稱不能為空")
            else:
                new_config = {'provider': sel_prov, 'api_key': api_key_input, 'base_url': base_url_input, 'validated': False}
                if sel_prov == "Pollinations.ai": new_config.update({'pollinations_auth_mode': auth_mode, 'pollinations_referrer': referrer, 'pollinations_token': token})
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
        if st.button("🔍 發現模型", use_container_width=True):
            with st.spinner("🔍 正在發現模型..."):
                discovered = auto_discover_flux_models(client, cfg['provider'], cfg['base_url'])
                st.session_state.discovered_models = discovered
                st.success(f"發現 {len(discovered)} 個模型！") if discovered else st.warning("未發現任何兼容模型。")
                time.sleep(1); rerun_app()
    else:
        st.error(f"🔴 '{st.session_state.active_profile_name}' 未配置或驗證")
    st.markdown("---")
    st.info(f"⚡ **免費版優化**\n- 歷史記錄: {MAX_HISTORY_ITEMS}\n- 收藏夾: {MAX_FAVORITE_ITEMS}")

st.title("🌟 Flux AI (最終完善版)")

# --- 主介面 ---
tab1, tab2, tab3 = st.tabs(["🚀 生成圖像", f"📚 歷史記錄 ({len(st.session_state.generation_history)})", f"⭐ 收藏夾 ({len(st.session_state.favorite_images)})"])

with tab1:
    if not api_configured:
        st.warning("⚠️ 請在側邊欄選擇一個已驗證的存檔。")
    else:
        all_models = merge_models()
        if not all_models:
            st.warning("⚠️ 未發現任何模型，請點擊側邊欄的「發現模型」。")
        else:
            prompt_default, neg_prompt_default = st.session_state.pop('vary_prompt', ''), st.session_state.pop('vary_negative_prompt', '')
            model_default_key = st.session_state.pop('vary_model', list(all_models.keys())[0])
            model_default_index = list(all_models.keys()).index(model_default_key) if model_default_key in all_models else 0
            
            sel_model = st.selectbox("模型:", list(all_models.keys()), index=model_default_index, format_func=lambda x: f"{all_models[x].get('icon', '🤖')} {all_models[x].get('name', x)}")
            st.info(f"**{all_models[sel_model].get('name')}**: {all_models[sel_model].get('description', 'N/A')}")
            
            selected_style = st.selectbox("🎨 風格預設:", list(STYLE_PRESETS.keys()))
            prompt_val = st.text_area("✍️ 提示詞:", value=prompt_default, height=100, placeholder="一隻貓在日落下飛翔，電影感，高品質")
            negative_prompt_val = st.text_area("🚫 負向提示詞:", value=neg_prompt_default, height=50, placeholder="模糊, 糟糕的解剖結構, 文字, 水印")
            
            col1, col2 = st.columns(2)
            with col1:
                # 使用新的尺寸選項
                size = st.selectbox("圖像尺寸", options=list(IMAGE_SIZES.keys()), format_func=lambda x: f"{IMAGE_SIZES[x]} ({x})")
            with col2:
                num_images = 1 if cfg['provider'] == "Pollinations.ai" else st.slider("生成數量", 1, MAX_BATCH_SIZE, 1)

            enhance, private, nologo = False, False, False
            if cfg['provider'] == "Pollinations.ai":
                with st.expander("🌸 Pollinations.ai 進階選項"):
                    enhance, private, nologo = st.checkbox("增強提示詞", value=True), st.checkbox("私密模式", value=True), st.checkbox("移除標誌", value=True)

            if st.button("🚀 生成圖像", type="primary", use_container_width=True, disabled=not prompt_val.strip()):
                final_prompt = f"{prompt_val}, {STYLE_PRESETS[selected_style]}" if selected_style != "無" else prompt_val
                with st.spinner(f"🎨 正在生成 {num_images} 張圖像..."):
                    params = {"model": sel_model, "prompt": final_prompt, "negative_prompt": negative_prompt_val, "n": num_images, "size": size, "enhance": enhance, "private": private, "nologo": nologo}
                    success, result = generate_images_with_retry(client, **params)
                    if success:
                        img_urls = [img.url for img in result.data]
                        add_to_history(prompt_val, negative_prompt_val, sel_model, img_urls, {"size": size, "provider": cfg['provider'], "style": selected_style})
                        st.success(f"✨ 成功生成 {len(img_urls)} 張圖像！")
                        cols = st.columns(min(len(img_urls), 2))
                        for i, url in enumerate(img_urls):
                            with cols[i % 2]: display_image_with_actions(url, f"{st.session_state.generation_history[0]['id']}_{i}", st.session_state.generation_history[0])
                        gc.collect()
                    else: st.error(f"❌ 生成失敗: {result}")

with tab2:
    if not st.session_state.generation_history: st.info("📭 尚無生成歷史。")
    else:
        for item in st.session_state.generation_history:
            with st.expander(f"🎨 {item['prompt'][:60]}... | {item['timestamp'].strftime('%m-%d %H:%M')}"):
                st.markdown(f"**提示詞**: {item['prompt']}\n\n**模型**: {merge_models().get(item['model'], {}).get('name', item['model'])}")
                if item.get('negative_prompt'): st.markdown(f"**負向提示詞**: {item['negative_prompt']}")
                cols = st.columns(min(len(item['images']), 2))
                for i, url in enumerate(item['images']):
                    with cols[i % 2]: display_image_with_actions(url, f"hist_{item['id']}_{i}", item)

with tab3:
    if not st.session_state.favorite_images: st.info("⭐ 尚無收藏的圖像。")
    else:
        cols = st.columns(3)
        for i, fav in enumerate(sorted(st.session_state.favorite_images, key=lambda x: x['timestamp'], reverse=True)):
            with cols[i % 3]: display_image_with_actions(fav['image_url'], fav['id'], fav.get('history_item'))

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>🌟 最終完善版 | 部署在 Koyeb 免費實例 🌟</small></div>""", unsafe_allow_html=True)

