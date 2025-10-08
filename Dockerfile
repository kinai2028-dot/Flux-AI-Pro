# 使用官方 Python 3.11 slim 鏡像作為基礎鏡像
FROM python:3.11-slim

# 設置工作目录
WORKDIR /app

# 設置環境變量以優化 Streamlit 運行
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 安裝構建 Python 包所需的最小系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY app.py .

# 創建一個非 root 用戶來運行應用，增強安全性
RUN useradd -ms /bin/bash streamlit
USER streamlit

# 暴露 Streamlit 運行的端口
EXPOSE 8501

# 添加健康檢查，以便容器編排工具可以監控應用狀態
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 容器啟動命令
CMD ["streamlit", "run", "app.py"]
