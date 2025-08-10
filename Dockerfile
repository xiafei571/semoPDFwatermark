FROM python:3.10-slim

WORKDIR /app

# 安装必要的系统依赖和中文字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY semoPDFwatermark/ /app/semoPDFwatermark/
COPY templates/ /app/templates/
COPY company_matrix/ /app/company_matrix/
COPY cab/ /app/cab/
COPY cab_manager.py /app/
COPY questions.csv /app/
COPY question-images/ /app/question-images/
COPY app.py /app/
COPY main.py /app/
COPY requirements_web.txt /app/

# 创建必要的目录
RUN mkdir -p /app/static /app/uploads /app/results

# 安装依赖
RUN pip install --no-cache-dir -r requirements_web.txt

# 设置环境变量
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 设置入口点
CMD ["python", "main.py"] 