# === 构建阶段 ===
FROM python:3.13-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 复制依赖清单，安装到系统 Python
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --system --no-install-project

# 复制源码
COPY main.py ./

# === 运行阶段 ===
FROM python:3.13-slim

# 时区 + opencv 依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo 'Asia/Shanghai' > /etc/timezone

WORKDIR /app

# 从 builder 复制已安装的依赖（系统 site-packages + 源码）
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app/main.py ./

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
