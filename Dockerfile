FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY semoPDFwatermark/ /app/semoPDFwatermark/
COPY templates/ /app/templates/
COPY app.py /app/
COPY requirements_web.txt /app/

# 创建必要的目录
RUN mkdir -p /app/static /app/uploads /app/results

# 安装依赖
RUN pip install --no-cache-dir -r requirements_web.txt

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["python", "app.py"] 