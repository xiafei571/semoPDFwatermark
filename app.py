import os
import shutil
import uuid
import zipfile
import tempfile
import time
import logging
from typing import List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from urllib.parse import quote
import json

from semoPDFwatermark import PDFWatermarker
from company_matrix.company_matrix_routes import company_matrix_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("pdf_watermark_app")

# 应用版本号
APP_VERSION = "1.1.2"

# 默认配置
DEFAULT_CONFIG = {
    "pagesize": "letter",
    "fontname": "Helvetica", 
    "fontsize": 60,
    "opacity": 0.3,
    "angle": 45,
    "color": "0,0,0"
}

# 创建应用
app = FastAPI(title="PDF水印添加工具")

# 包含company_matrix路由
app.include_router(company_matrix_router, prefix="/company-matrix", tags=["company-matrix"])

# 创建必要的目录
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# 设置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页 - 工具集展示"""
    return templates.TemplateResponse("home.html", {"request": request, "version": APP_VERSION})


@app.get("/pdf-watermark", response_class=HTMLResponse)
async def pdf_watermark_page(request: Request):
    """PDF水印工具页面"""
    return templates.TemplateResponse("index.html", {"request": request, "version": APP_VERSION})


@app.post("/add-watermark")
async def add_watermark(
    request: Request,
    files: List[UploadFile] = File(...),
    watermark_text: str = Form(...),
    pagesize: str = Form("letter"),
    fontname: str = Form("Helvetica"),
    fontsize: int = Form(60),
    opacity: float = Form(0.3),
    angle: float = Form(45),
    color: str = Form("0,0,0"),
):
    """处理上传的PDF文件并添加水印"""
    logger.info("="*50)
    logger.info(f"收到添加水印请求，共 {len(files)} 个文件")
    for i, file in enumerate(files):
        logger.info(f"文件 {i+1}: {file.filename}, 内容类型: {file.content_type}")
    logger.info(f"水印文本: {watermark_text}")
    logger.info(f"页面大小: {pagesize}, 字体: {fontname}, 大小: {fontsize}")
    logger.info(f"不透明度: {opacity}, 角度: {angle}, 颜色: {color}")
    logger.info("="*50)
    
    if not files:
        logger.warning("没有接收到文件")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": "请选择至少一个PDF文件", "version": APP_VERSION}
        )
    
    # 处理颜色参数
    try:
        color_tuple = tuple(float(c) for c in color.split(','))
        if len(color_tuple) != 3:
            raise ValueError("颜色参数必须是3个由逗号分隔的数字")
    except ValueError as e:
        logger.error(f"颜色格式错误: {str(e)}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": f"颜色格式错误: {str(e)}", "version": APP_VERSION}
        )
    
    # 创建一个会话ID用于保存文件
    session_id = str(uuid.uuid4())
    session_dir = os.path.join("results", session_id)
    os.makedirs(session_dir, exist_ok=True)
    logger.info(f"创建会话目录: {session_dir}")
    
    # 保存上传的文件
    saved_files = []
    result_files = []
    
    try:
        watermarker = PDFWatermarker()
        watermarker.set_pagesize(pagesize)
        
        # 预处理所有文件，读取内容并保存到临时文件
        temp_files = []
        for i, file in enumerate(files):
            if not file.filename.lower().endswith('.pdf'):
                logger.warning(f"跳过非PDF文件: {file.filename}")
                continue
            
            try:
                # 读取文件内容
                content = await file.read()
                if not content:
                    logger.warning(f"文件内容为空: {file.filename}")
                    continue
                
                content_size = len(content)
                logger.info(f"读取文件: {file.filename}, 大小: {content_size} 字节")
                
                # 生成临时文件名并保存 - 确保使用tempfile
                temp_fd, file_path = tempfile.mkstemp(suffix='.pdf', prefix=f'upload_{i}_')
                os.close(temp_fd)
                
                with open(file_path, "wb") as f:
                    f.write(content)
                
                # 检查文件大小
                actual_size = os.path.getsize(file_path)
                if actual_size == 0:
                    logger.error(f"临时文件为空: {file_path}")
                    continue
                
                logger.info(f"保存到临时文件: {file_path}, 实际大小: {actual_size} 字节")
                saved_files.append(file_path)
                
                # 将文件信息存储起来以供后续处理
                temp_files.append({
                    "file_path": file_path,
                    "filename": file.filename,
                    "size": content_size
                })
            except Exception as e:
                logger.error(f"读取或保存文件时出错: {file.filename}, {str(e)}")
                continue
        
        logger.info(f"预处理完成，有效PDF文件: {len(temp_files)} 个")
        
        # 处理所有已保存的文件
        for i, file_info in enumerate(temp_files):
            try:
                file_path = file_info["file_path"]
                original_filename = file_info["filename"]
                
                logger.info(f"开始处理文件 {i+1}/{len(temp_files)}: {original_filename}")
                
                # 验证临时文件是否有效
                if not os.path.exists(file_path):
                    logger.error(f"临时文件不存在: {file_path}")
                    continue
                
                if os.path.getsize(file_path) == 0:
                    logger.error(f"临时文件大小为0: {file_path}")
                    continue
                
                # 设置输出文件
                output_filename = f"watermarked_{original_filename}"
                output_path = os.path.join(session_dir, output_filename)
                
                logger.info(f"添加水印: {file_path} -> {output_path}")
                
                # 添加水印
                start_time = time.time()
                success = watermarker.add_watermark(
                    file_path,
                    watermark_text,
                    output_path,
                    fontname=fontname,
                    fontsize=fontsize,
                    opacity=opacity,
                    angle=angle,
                    color=color_tuple
                )
                end_time = time.time()
                
                if success == "ENCRYPTED_PDF":
                    logger.warning(f"文件加密无法处理: {original_filename}")
                    result_files.append({
                        "original": original_filename,
                        "processed": None,
                        "download_url": None,
                        "encrypted": True
                    })
                elif success:
                    output_size = os.path.getsize(output_path)
                    logger.info(f"成功添加水印: {output_path}, 大小: {output_size} 字节, 耗时: {end_time - start_time:.2f}秒")
                    
                    result_files.append({
                        "original": original_filename,
                        "processed": output_filename,
                        "download_url": f"/download/{session_id}/{output_filename}",
                        "encrypted": False
                    })
                else:
                    logger.error(f"添加水印失败: {original_filename}")
            except Exception as e:
                logger.exception(f"处理文件 {file_info['filename']} 时出错")
                continue
    
    except Exception as e:
        logger.exception("处理文件时出错")
        
        # 清理会话文件
        for file in saved_files:
            if os.path.exists(file):
                os.remove(file)
        
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": f"处理文件时出错: {str(e)}", "version": APP_VERSION}
        )
    
    finally:
        # 处理完成后删除临时文件
        for file in saved_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
                    logger.info(f"删除临时文件: {file}")
            except Exception as e:
                logger.error(f"删除临时文件出错: {file}, {str(e)}")
    
    logger.info(f"处理结果: 成功 {len([r for r in result_files if not r.get('encrypted', False)])} / {len(temp_files)} 个文件 (排除加密文件)")
    
    # 如果没有成功处理任何文件，返回错误
    if not any(not r.get('encrypted', False) for r in result_files):
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            logger.info(f"删除会话目录: {session_dir}")
            
        # 检查是否所有文件都是加密的
        if all(r.get('encrypted', False) for r in result_files) and result_files:
            logger.warning("所有PDF文件都是加密的，无法处理")
            return templates.TemplateResponse(
                "index.html", 
                {"request": request, "error": "所有PDF文件都是加密的，无法处理", "version": APP_VERSION}
            )
        else:
            logger.warning("没有找到有效的PDF文件进行处理")
            return templates.TemplateResponse(
                "index.html", 
                {"request": request, "error": "没有找到有效的PDF文件进行处理", "version": APP_VERSION}
            )
    
    # 保存配置参数到配置文件
    config = {
        "watermark_text": watermark_text,
        "pagesize": pagesize,
        "fontname": fontname,
        "fontsize": fontsize,
        "opacity": opacity,
        "angle": angle,
        "color": color,
        "files": [r["original"] for r in result_files]
    }
    
    # 保存配置到文件
    with open(os.path.join(session_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"保存配置到: {os.path.join(session_dir, 'config.json')}")
    
    # 计算处理统计
    encrypted_count = sum(1 for r in result_files if r.get('encrypted', False))
    successful_count = sum(1 for r in result_files if not r.get('encrypted', False))
    total_count = len(result_files)
    
    logger.info("="*50)
    logger.info(f"处理完成，返回结果页面，成功处理 {successful_count}/{total_count} 个文件，其中加密文件: {encrypted_count}个")
    logger.info("="*50)
    
    # 返回结果页面
    return templates.TemplateResponse(
        "result.html", {
            "request": request,
            "results": result_files,
            "session_id": session_id,
            "version": APP_VERSION,
            "encrypted_count": encrypted_count,
            "successful_count": successful_count,
            "total_count": total_count
        }
    )


@app.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str, request: Request):
    """下载处理后的文件"""
    file_path = os.path.join("results", session_id, filename)
    if not os.path.exists(file_path):
        return {"error": "文件不存在"}
    
    # 获取请求头中的Referer，检查是否带有download参数
    referer = request.headers.get("referer", "")
    is_download = "download" in referer or request.headers.get("sec-fetch-dest") == "download"
    
    headers = {}
    if is_download:
        # 如果是下载请求，设置Content-Disposition为attachment
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
    else:
        # 如果是预览请求，设置Content-Disposition为inline
        headers["Content-Disposition"] = f"inline; filename*=UTF-8''{quote(filename)}"
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
        headers=headers
    )


@app.get("/download-all/{session_id}")
async def download_all(session_id: str):
    """将所有处理后的文件打包下载"""
    session_dir = os.path.join("results", session_id)
    if not os.path.exists(session_dir):
        return {"error": "会话不存在"}
    
    # 确保目录中有文件
    files = os.listdir(session_dir)
    if not files:
        return {"error": "没有可下载的文件"}
    
    # 创建压缩文件
    zip_filename = f"watermarked_pdfs_{session_id}.zip"
    zip_path = os.path.join("results", zip_filename)
    
    # 使用zipfile模块创建ZIP文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            file_path = os.path.join(session_dir, file)
            if os.path.isfile(file_path) and not file.endswith("config.json"):
                zipf.write(file_path, arcname=file)
    
    # 设置响应头，确保作为附件下载
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(zip_filename)}"
    }
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename,
        headers=headers
    )


@app.get("/regenerate/{session_id}")
async def regenerate(request: Request, session_id: str):
    """使用保存的配置重新生成水印"""
    config_path = os.path.join("results", session_id, "config.json")
    
    # 如果配置文件不存在，则重定向到首页
    if not os.path.exists(config_path):
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": "配置信息不存在，无法重新生成", "version": APP_VERSION}
        )
    
    # 读取配置文件
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 返回带有预填参数的首页
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "config": config,  # 传递配置参数
            "version": APP_VERSION
        }
    )


# 添加健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


# 只有在直接运行此文件时才启动服务器
if __name__ == "__main__":
    import uvicorn
    # 获取PORT环境变量，如果不存在则默认为8000
    port = int(os.environ.get("PORT", 8000))
    
    # 打印启动信息
    print(f"Starting server on port {port}...")
    
    # 启动服务器，监听所有网络接口
    uvicorn.run(app, host="0.0.0.0", port=port) 