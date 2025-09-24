import streamlit as st
from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO
import datetime
import base64
from typing import Dict, List, Optional, Tuple
import time
import random
import json
import uuid
import os
import re
from urllib.parse import urlencode, quote
import gc  # 引入記憶體回收模組

# 優化：為免費方案設定更嚴格的限制
MAX_HISTORY_ITEMS = 15
MAX_FAVORITE_ITEMS = 30

# 兼容性函數
def rerun_app():
    """兼容不同 Streamlit 版本的重新運行函數"""
    if hasattr(st, 'rerun'):
        st.rerun()
    elif hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else:
        st.stop()

# 設定頁面配置
st.set_page_config(
    page_title="Flux AI (Free Tier Optimized)",
    page_icon="⚡",
    layout="wide"
)

# API 提供商配置
API_PROVIDERS = {
    "OpenAI Compatible": {
        "name": "OpenAI Compatible API",
        "base_url_default": "https://api.openai.com/v1",
        "key_prefix": "sk-",
        "description": "OpenAI 官方或兼容的 API 服務",
        "icon": "🤖"
    },
    "Navy": {
        "name": "Navy API",
        "base_url_default": "https://api.navy/v1",
        "key_prefix": "sk-",
        "description": "Navy 提供的 AI 圖像生成服務",
        "icon": "⚓"
    },
    "Pollinations.ai": {
        "name": "Pollinations.ai",
        "base_url_default": "https://image.pollinations.ai",
        "key_prefix": "",
        "description": "支援免費和認證模式的圖像生成 API",
        "icon": "🌸",
        "auth_modes": ["free", "referrer", "token"]
    },
    "Hugging Face": {
        "name": "Hugging Face Inference",
        "base_url_default": "https://api-inference.huggingface.co",
        "key_prefix": "hf_",
        "description": "Hugging Face Inference API",
        "icon": "🤗"
    },
    "Custom": {
        "name": "自定義 API",
        "base_url_default": "",
        "key_prefix": "",
        "description": "自定義的 API 端點",
        "icon": "🔧"
    }
}

# 基礎 Flux 模型配置
BASE_FLUX_MODELS = {
    "flux.1-schnell": {
        "name": "FLUX.1 Schnell",
        "description": "最快的生成速度，開源模型",
        "icon": "⚡",
        "type": "快速生成",
        "priority": 1,
        "source": "base",
        "auth_required": False
    },
    "flux.1-dev": {
        "name": "FLUX.1 Dev",
        "description": "開發版本，平衡速度與質量",
        "icon": "🔧",
        "type": "開發版本",
        "priority": 2,
        "source": "base",
        "auth_required": False
    }
}

# 模型自動發現規則
FLUX_MODEL_PATTERNS = {
    r'flux[\\.\\-]?1[\\.\\-]?schnell': {
        "name_template": "FLUX.1 Schnell", "icon": "⚡", "type": "快速生成", "priority_base": 100, "auth_required": False
    },
    r'flux[\\.\\-]?1[\\.\\-]?dev': {
        "name_template": "FLUX.1 Dev", "icon": "🔧", "type": "開發版本", "priority_base": 200, "auth_required": False
    },
    r'flux[\\.\\-]?1[\\.\\-]?pro': {
        "name_template": "FLUX.1 Pro", "icon": "👑", "type": "專業版本", "priority_base": 300, "auth_required": False
    },
    r'flux[\\.\\-]?1[\\.\\-]?kontext|kontext': {
        "name_template": "FLUX.1 Kontext", "icon": "🎯", "type": "上下文理解", "priority_base": 400, "auth_required": True
    }
}

HF_FLUX_ENDPOINTS = [
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/FLUX.1-dev",
]

def auto_discover_flux_models(client, provider: str, api_key: str, base_url: str) -> Dict[str, Dict]:
    discovered_models = {}
    try:
        if provider == "Pollinations.ai":
            response = requests.get(f"{base_url}/models", timeout=10)
            if response.status_code == 200:
                for model_name in response.json():
                    model_info = analyze_model_name(model_name)
                    model_info.update({'source': 'pollinations', 'type': '圖像專用', 'icon': '🌸'})
                    discovered_models[model_name] = model_info
        elif provider == "Hugging Face":
            for endpoint in HF_FLUX_ENDPOINTS:
                model_id = endpoint.split('/')[-1]
                model_info = analyze_model_name(model_id, endpoint)
                model_info.update({'source': 'huggingface', 'endpoint': endpoint})
                discovered_models[model_id] = model_info
        else:
            for model in client.models.list().data:
                if 'flux' in model.id.lower() or 'kontext' in model.id.lower():
                    model_info = analyze_model_name(model.id)
                    model_info['source'] = 'api_discovery'
                    discovered_models[model.id] = model_info
        return discovered_models
    except Exception as e:
        st.warning(f"模型自動發現失敗: {e}")
        return {}

def analyze_model_name(model_id: str, full_path: str = None) -> Dict:
    model_lower = model_id.lower()
    for pattern, info in FLUX_MODEL_PATTERNS.items():
        if re.search(pattern, model_lower):
            analyzed_info = {
                "name": info["name_template"], "icon": info["icon"], "type": info["type"],
                "description": f"自動發現的 {info['name_template']} 模型",
                "priority": info["priority_base"] + hash(model_id) % 100,
                "auto_discovered": True, "auth_required": info.get("auth_required", False)
            }
            if full_path:
                analyzed_info["full_path"] = full_path
                if '/' in full_path:
                    analyzed_info["name"] += f" ({full_path.split('/')[0]})"
            return analyzed_info
    return {"name": model_id.replace('-', ' ').replace('_', ' ').title(), "icon": "🤖", "type": "自動發現", "description": f"自動發現的模型: {model_id}", "priority": 999, "auto_discovered": True, "auth_required": 'kontext' in model_lower, "full_path": full_path or model_id}

def merge_models() -> Dict[str, Dict]:
    merged_models = {**BASE_FLUX_MODELS, **st.session_state.get('discovered_models', {})}
    return dict(sorted(merged_models.items(), key=lambda item: item[1].get('priority', 999)))

def validate_api_key(api_key: str, base_url: str, provider: str) -> Tuple[bool, str]:
    try:
        if provider == "Pollinations.ai":
            return (True, "Pollinations.ai 連接成功") if requests.get(f"{base_url}/models", timeout=10).status_code == 200 else (False, "連接失敗")
        elif provider == "Hugging Face":
            headers = {"Authorization": f"Bearer {api_key}"}
            return (True, "Hugging Face API 驗證成功") if requests.get(f"{base_url}/models/black-forest-labs/FLUX.1-schnell", headers=headers, timeout=10).status_code == 200 else (False, "驗證失敗")
        else:
            OpenAI(api_key=api_key, base_url=base_url).models.list()
            return True, "API 密鑰驗證成功"
    except Exception as e:
        return False, f"API 驗證失敗: {e}"

def generate_images_with_retry(client, provider: str, api_key: str, base_url: str, **params) -> Tuple[bool, any]:
    for attempt in range(3):
        try:
            if provider == "Pollinations.ai":
                p = {k: v for k, v in {"model": params.get("model"), "width": params.get("size", "1024x1024").split('x')[0], "height": params.get("size", "1024x1024").split('x')[1], "seed": random.randint(0, 1000000), "nologo": "true"}.items() if v is not None}
                headers, cfg = {}, st.session_state.get('api_config', {})
                if (auth_mode := cfg.get('pollinations_auth_mode', 'free')) == 'token' and cfg.get('pollinations_token'):
                    headers['Authorization'] = f"Bearer {cfg['pollinations_token']}"
                elif auth_mode == 'referrer' and cfg.get('pollinations_referrer'):
                    headers['Referer'] = cfg['pollinations_referrer']
                response = requests.get(f"{base_url}/prompt/{quote(params.get('prompt', ''))}?{urlencode(p)}", headers=headers, timeout=120)
                if response.ok: return True, type('MockResponse', (object,), {'data': [type('obj', (object,), {'url': f"data:image/png;base64,{base64.b64encode(response.content).decode()}"})()]})()
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            elif provider == "Hugging Face":
                headers, data = {"Authorization": f"Bearer {api_key}"}, {"inputs": params.get("prompt", "")}
                model_name = params.get("model", "FLUX.1-schnell")
                endpoint_path = merge_models().get(model_name, {}).get('full_path', f"black-forest-labs/{model_name}")
                response = requests.post(f"{base_url}/models/{endpoint_path}", headers=headers, json=data, timeout=60)
                if response.ok: return True, type('MockResponse', (object,), {'data': [type('obj', (object,), {'url': f"data:image/png;base64,{base64.b64encode(response.content).decode()}"})()]})()
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            else:
                return True, client.images.generate(**params)
        except Exception as e:
            if attempt < 2 and ("500" in str(e) or "timeout" in str(e).lower()):
                time.sleep((attempt + 1) * 2)
                continue
            return False, str(e)
    return False, "所有重試均失敗"

def init_session_state():
    defaults = {
        'api_config': {'provider': 'Navy', 'api_key': '', 'base_url': 'https://api.navy/v1', 'validated': False, 'pollinations_auth_mode': 'free', 'pollinations_token': '', 'pollinations_referrer': ''},
        'generation_history': [], 'favorite_images': [], 'discovered_models': {}
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def add_to_history(prompt: str, model: str, images: List[str], metadata: Dict):
    history = st.session_state.generation_history
    history.insert(0, {"id": str(uuid.uuid4()), "timestamp": datetime.datetime.now(), "prompt": prompt, "model": model, "images": images, "metadata": metadata})
    st.session_state.generation_history = history[:MAX_HISTORY_ITEMS]

def display_image_with_actions(image_url: str, image_id: str, history_item: Dict = None):
    try:
        img_data = base64.b64decode(image_url.split(',')[1]) if image_url.startswith('data:image') else requests.get(image_url, timeout=10).content
        img = Image.open(BytesIO(img_data))
        st.image(img, use_column_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 下載", img_data, f"flux_{image_id}.png", "image/png", key=f"dl_{image_id}", use_container_width=True)
        with col2:
            is_fav = any(fav['id'] == image_id for fav in st.session_state.favorite_images)
            if st.button("⭐ 已收藏" if is_fav else "☆ 收藏", key=f"fav_{image_id}", use_container_width=True):
                if is_fav:
                    st.session_state.favorite_images = [f for f in st.session_state.favorite_images if f['id'] != image_id]
                elif len(st.session_state.favorite_images) < MAX_FAVORITE_ITEMS:
                    st.session_state.favorite_images.append({"id": image_id, "image_url": image_url, "timestamp": datetime.datetime.now(), "history_item": history_item})
                else:
                    st.warning(f"收藏夾已滿 (上限 {MAX_FAVORITE_ITEMS} 張)")
                rerun_app()
    except Exception as e:
        st.error(f"圖像顯示錯誤: {e}")

def init_api_client():
    cfg = st.session_state.api_config
    if cfg.get('provider') not in ["Hugging Face", "Pollinations.ai"] and cfg.get('api_key'):
        try: return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
        except Exception: return None
    return None

def show_api_settings():
    st.subheader("🔑 API 設置")
    provs = list(API_PROVIDERS.keys())
    sel_prov = st.selectbox("選擇 API 提供商", provs, index=provs.index(st.session_state.api_config.get('provider', 'Navy')), format_func=lambda x: f"{API_PROVIDERS[x]['icon']} {API_PROVIDERS[x]['name']}")
    prov_info = API_PROVIDERS[sel_prov]
    st.info(f"📋 {prov_info['description']}")
    
    key_req = sel_prov not in ["Pollinations.ai"]
    key_in = st.text_input("API 密鑰", type="password", placeholder=f"輸入 {prov_info['name']} 的 API 密鑰...") if key_req else "N/A"
    url_in = st.text_input("API 端點 URL", value=prov_info['base_url_default'] if sel_prov != st.session_state.api_config.get('provider') else st.session_state.api_config.get('base_url', prov_info['base_url_default']))
    
    if st.button("💾 保存並測試", type="primary"):
        final_key = key_in if key_in and key_in != "N/A" else st.session_state.api_config.get('api_key', '')
        if key_req and not final_key: st.error("❌ 請輸入 API 密鑰")
        else:
            with st.spinner("正在驗證並保存..."):
                is_valid, msg = validate_api_key(final_key, url_in, sel_prov)
                st.session_state.api_config.update({'provider': sel_prov, 'api_key': final_key, 'base_url': url_in, 'validated': is_valid})
                st.session_state.discovered_models = {}
                if is_valid: st.success(f"✅ {msg}，設置已保存。")
                else: st.error(f"❌ {msg}")
                time.sleep(1)
                rerun_app()

def auto_discover_models():
    cfg = st.session_state.api_config
    if (cfg.get('provider') not in ["Pollinations.ai"]) and not cfg.get('api_key'): st.error("❌ 請先配置 API 密鑰"); return
    with st.spinner("🔍 正在自動發現模型..."):
        client = init_api_client()
        discovered = auto_discover_flux_models(client, cfg['provider'], cfg['api_key'], cfg['base_url'])
        new_count = len(set(discovered.keys()) - set(st.session_state.discovered_models.keys()) - set(BASE_FLUX_MODELS.keys()))
        st.session_state.discovered_models = discovered
        if new_count > 0: st.success(f"✅ 發現 {new_count} 個新模型！")
        elif discovered: st.info("ℹ️ 已刷新模型列表，未發現新模型。")
        else: st.warning("⚠️ 未發現任何兼容模型。")
        time.sleep(1)
        rerun_app()

init_session_state()
client = init_api_client()
cfg = st.session_state.api_config
api_configured = cfg.get('validated', False)

with st.sidebar:
    show_api_settings()
    st.markdown("---")
    if api_configured:
        st.success(f"🟢 {cfg['provider']} API 已配置")
        if st.button("🔍 發現模型", use_container_width=True): auto_discover_models()
    else:
        st.error("🔴 API 未配置或未驗證")
    st.markdown("---")
    st.info(f"⚡ **免費版優化**\n- 歷史記錄上限: {MAX_HISTORY_ITEMS} 條\n- 收藏夾上限: {MAX_FAVORITE_ITEMS} 張")

st.title("🎨 Flux AI 圖像生成器 (Free Tier)")

tab1, tab2, tab3 = st.tabs(["🚀 圖像生成", f"📚 歷史 ({len(st.session_state.generation_history)})", f"⭐ 收藏 ({len(st.session_state.favorite_images)})"])

with tab1:
    if not api_configured:
        st.warning("⚠️ 請先在側邊欄配置並驗證 API")
    else:
        all_models = merge_models()
        if not all_models:
            st.warning("⚠️ 尚未發現任何模型，請點擊側邊欄的「發現模型」")
        else:
            model_opts = list(all_models.keys())
            sel_model = st.selectbox("選擇模型:", model_opts, format_func=lambda x: f"{all_models[x].get('icon', '🤖')} {all_models[x].get('name', x)}" + (" 🔐" if all_models[x].get('auth_required', False) else ""))
            st.info(f"**{all_models[sel_model].get('name')}**: {all_models[sel_model].get('description', 'N/A')}")
            
            prompt_val = st.text_area("輸入提示詞:", height=100, placeholder="一隻貓在日落下飛翔，電影感，高品質")
            
            size = st.selectbox("圖像尺寸", ["1024x1024", "1152x896", "896x1152", "1344x768", "768x1344"], index=0)
            
            if st.button("🚀 生成圖像", type="primary", use_container_width=True, disabled=not prompt_val.strip()):
                with st.spinner(f"🎨 使用 {all_models[sel_model].get('name')} 生成中..."):
                    success, result = generate_images_with_retry(client, cfg['provider'], cfg['api_key'], cfg['base_url'], model=sel_model, prompt=prompt_val, n=1, size=size)
                    if success:
                        img_urls = [img.url for img in result.data]
                        add_to_history(prompt_val, sel_model, img_urls, {"size": size, "provider": cfg['provider']})
                        st.success("✨ 圖像生成成功！")
                        display_image_with_actions(img_urls[0], f"{st.session_state.generation_history[0]['id']}_0", st.session_state.generation_history[0])
                        gc.collect() # 優化：生成後立即回收記憶體
                    else:
                        st.error(f"❌ 生成失敗: {result}")

with tab2:
    if st.session_state.generation_history:
        for item in st.session_state.generation_history:
            with st.expander(f"🎨 {item['prompt'][:60]}... | {item['timestamp'].strftime('%m-%d %H:%M')}"):
                st.markdown(f"**提示詞**: {item['prompt']}\n\n**模型**: {merge_models().get(item['model'], {}).get('name', item['model'])}")
                display_image_with_actions(item['images'][0], f"hist_{item['id']}_0", item)
    else: st.info("📭 尚無生成歷史")

with tab3:
    if st.session_state.favorite_images:
        cols = st.columns(3)
        for i, fav in enumerate(sorted(st.session_state.favorite_images, key=lambda x: x['timestamp'], reverse=True)):
            with cols[i % 3]:
                display_image_with_actions(fav['image_url'], fav['id'], fav.get('history_item'))
    else: st.info("⭐ 尚無收藏圖像")

st.markdown("""<div style="text-align: center; color: #888; margin-top: 2rem;"><small>⚡ 部署在 Koyeb 免費實例 | 為低記憶體環境優化 ⚡</small></div>""", unsafe_allow_html=True)
