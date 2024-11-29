# 使用官方 Python 镜像
FROM python:3.9-slim

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制项目代码
COPY . .

# 安装 PDM
RUN pip install pdm

# 安装项目依赖
RUN pdm install



# 暴露端口 8000
EXPOSE 5000

# 设置环境变量
ENV MODEL_ID="sv30-v2/7"
ENV GET_IMAGE_URL="http://sv30_camera:8080/ipccamera/getimg/localcamera-0"
ENV API_URL="http://inference-server-cpu:9001"
ENV API_KEY="token"

# 设置启动命令
CMD ["pdm", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

