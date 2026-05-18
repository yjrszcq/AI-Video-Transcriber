# AI视频转录器 Docker镜像 — Python 与本地推荐环境对齐（3.12），依赖与 requirements.txt 一致
FROM python:3.12-slim-bookworm

WORKDIR /app

# 系统依赖（FFmpeg：链接下载与本地上传转码）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 先升级 pip，再按 requirements 安装（与本地 `pip install -r requirements.txt` 行为一致，取满足下界的最新版）
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Hugging Face / faster-whisper 缓存目录
# 构建期预下载模型保存在镜像内目录，运行期缓存使用可挂载目录。
ENV PRELOADED_HF_HOME=/opt/preloaded-hf-cache
ENV HF_HOME=/data/huggingface
ENV HUGGINGFACE_HUB_CACHE=/data/huggingface/hub

# 是否在镜像构建阶段预下载 Whisper 模型
# none = 不下载模型，即 standard/latest
# base = 只下载 base 模型
# all  = 下载常用 Whisper 模型
ARG PRELOAD_WHISPER_MODELS=none

RUN if [ "$PRELOAD_WHISPER_MODELS" = "base" ]; then \
      HF_HOME="$PRELOADED_HF_HOME" HUGGINGFACE_HUB_CACHE="$PRELOADED_HF_HOME/hub" \
      python -c "from faster_whisper.utils import download_model; download_model('base')"; \
    elif [ "$PRELOAD_WHISPER_MODELS" = "all" ]; then \
      HF_HOME="$PRELOADED_HF_HOME" HUGGINGFACE_HUB_CACHE="$PRELOADED_HF_HOME/hub" \
      python -c "from faster_whisper.utils import download_model; [download_model(m) for m in ['tiny','base','small','medium','large-v3']]"; \
    else \
      echo 'Skip Whisper model preload'; \
    fi

# 复制项目文件
COPY . .

# 创建临时目录和运行期缓存目录
RUN mkdir -p temp "$HF_HOME"

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV WHISPER_MODEL_SIZE=base
ENV UPLOAD_MAX_MB=200
ENV SSE_HEARTBEAT_SECONDS=10

# 暴露端口
EXPOSE 8000

# 首次启动时，如果运行期缓存为空，则复制镜像内预下载模型。
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
CMD ["python3", "start.py", "--prod"]
