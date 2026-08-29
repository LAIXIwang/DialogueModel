# 后端镜像：对话 BFF（8000）与管理平台（8001）共用同一镜像，仅启动命令不同
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 先装依赖（利用构建缓存）
COPY python-project/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端全部代码（app/ 对话BFF + admin/ 管理平台 + tools/ 模拟上游）
COPY python-project/ .

EXPOSE 8000 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
