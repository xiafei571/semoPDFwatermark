#!/usr/bin/env python3
"""
Cloud Run 启动脚本
"""
import os
import uvicorn
from app import app

if __name__ == "__main__":
    # 获取PORT环境变量，Cloud Run会提供这个变量
    port = int(os.environ.get("PORT", 8080))
    
    # 打印启动信息
    print(f"Starting server on port {port}...")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    
    # 启动服务器，监听所有网络接口
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    ) 