#!/usr/bin/env python3
"""
Cloud Run 启动脚本 - PDF水印工具和公司矩阵生成器 v1.1
"""
import os
import uvicorn

def main():
    """主启动函数"""
    # 获取PORT环境变量，Cloud Run会提供这个变量
    port = int(os.environ.get("PORT", 8080))
    environment = os.environ.get("ENVIRONMENT", "production")
    
    # 打印启动信息
    print(f"Starting PDF Watermark & Company Matrix Tools v1.1...")
    print(f"Port: {port}")
    print(f"Environment: {environment}")
    print(f"Host: 0.0.0.0")
    
    # 启动服务器配置
    uvicorn_config = {
        "app": "app:app",
        "host": "0.0.0.0",
        "port": port,
        "log_level": "info",
        "access_log": True
    }
    
    # 生产环境优化
    if environment == "production":
        uvicorn_config.update({
            "workers": 1,
            "loop": "uvloop" if os.name != "nt" else "asyncio"
        })
    
    # 启动服务器
    uvicorn.run(**uvicorn_config)

if __name__ == "__main__":
    main() 