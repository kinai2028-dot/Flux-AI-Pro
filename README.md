🚀 FLUX AI 終極版 - 一個強大的多模型 AI 圖像生成器
這是一個基於 Streamlit 構建的、功能豐富的 AI 圖像生成 Web 應用。它不僅僅是一個簡單的界面，而是一個集成了多 API 供應商、多模型支持、配置持久化和高級用戶體驗的終極工具。

這個項目的目標是提供一個統一、流暢且高度可配置的界面，讓用戶可以輕鬆地利用包括 FLUX 家族在內的各種頂級 AI 圖像生成模型進行創作。

[<!-- 請替換為您自己的應用截圖 URL -->](https://thumbsnap.com/t/HTGHoE13.jpg)
🏆 核心功能
多 API 供應商支持:

原生支持 Pollinations.ai、NavyAI 以及任何 OpenAI 兼容的 API 端點。

可在不同供應商之間無縫切換。

配置永久化 (st.secrets):

通過 Streamlit 的 secrets 功能實現 API 存檔的永久保存。配置一次，永久有效，應用重啟或重新部署後數據不會丟失。

即使沒有配置 Secrets，應用也能健壯地啟動，不會崩潰。

豐富的模型支持:

手動擴充支持最新的 FLUX 模型家族，包括 flux-1.1-pro, flux.1-kontext-pro, flux.1-kontext-max, flux-dev, 和 flux-schnell。

支持自動模型發現，可動態加載 API 端點支持的所有兼容模型。

批量生成:

支持一次性生成多張圖片（最多 4 張），極大地提升了創作和篩選效率。

通過應用層並行請求，為不支持批量生成的 Pollinations.ai 實現了無縫的多圖生成體驗。

21 種藝術風格預設:

內置從「電影感」、「賽博龐克」到「水墨畫」、「黑白線條藝術」等 21 種精心調校的藝術風格，一鍵應用。

流暢的 API 管理:

在側邊欄提供了直觀的 UI，可以新增、刪除、編輯 API 存檔。

編輯器具有智能 URL 自動更新功能，當您切換 API 供應商時，端點 URL 會自動填充為該供應商的預設值。

完整的用戶工作流:

生成歷史：自動保存最近的生成記錄，方便回溯和比較。

我的收藏：一鍵收藏您喜歡的圖片。

圖像變體：基於歷史或收藏中的任何一張圖片，可以一鍵「復用提示詞」來生成新的變體。

🛠️ 技術棧
前端框架: Streamlit

核心庫: openai, requests, Pillow

推薦部署平台: Koyeb (免費方案)

🚀 部署指南 (針對 Koyeb 免費方案)
在 Koyeb 上部署此應用非常簡單，因為它對 Python 和 Streamlit 提供了出色的支持。

1. 項目文件結構
您的項目在根目錄下僅需包含兩個文件：

text
.
├── app.py               # 主應用程式碼
└── requirements.txt     # Python 依賴
您也可以選擇在本地創建 .streamlit/secrets.toml 文件用於開發測試。

2. 文件內容
app.py:

使用我們在對話中確認的**「終極模型版」**完整程式碼。

requirements.txt:

text
streamlit
openai
requests
Pillow
3. Koyeb 部署步驟
推送到 GitHub: 將包含以上兩個文件的項目文件夾推送到一個新的或現有的 GitHub 儲存庫。

登錄 Koyeb: 使用您的 GitHub 帳戶登錄 Koyeb。

創建 Web Service:

在 Koyeb 儀表板上，點擊「Create Service」，然後選擇「Web Service」。

選擇 GitHub 作為部署方式，並選擇您的儲存庫。

配置服務 (關鍵步驟):

Koyeb 會自動檢測到 requirements.txt 文件，並將其識別為 Python 項目。

在 "Builder" 部分，您需要覆蓋運行命令。

點擊「Run command」字段旁邊的「Override」開關，並輸入以下命令：

bash
streamlit run app.py --server.port=$PORT
這是確保 Koyeb 能在正確的端口上啟動 Streamlit 服務的關鍵步驟。

設置 Secrets (用於永久存檔):

為了啟用永久存檔功能，您必須設置環境變量。

在您服務的「Settings」標籤頁下，進入「Environment Variables」部分。

點擊「Add Variable」，然後選擇「Secret」。

將名稱 (Name) 設置為 STREAMLIT_SECRETS。

在值 (Value) 中，粘貼您本地 secrets.toml 文件的全部內容。secrets.toml 示例如下：

text
# 您本地 .streamlit/secrets.toml 文件的內容
[api_profiles.我的NavyAI]
provider = "NavyAI"
api_key = "sk-your-navy-api-key-here"
base_url = "https://api.navy/v1"
validated = true

[api_profiles.我的Pollinations]
provider = "Pollinations.ai"
base_url = "https://image.pollinations.ai"
validated = true
pollinations_auth_mode = "免費"
部署與訪問:

點擊「Deploy」按鈕。Koyeb 將開始構建和部署您的應用。

完成後，您將獲得一個公開的 .koyeb.app 網址。點擊它，即可訪問您功能完備的 AI 圖像生成器！
