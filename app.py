#!/usr/bin/env python3
"""
PDF水印工具和公司矩阵生成器
多功能Web应用 - 版本 1.1
"""

import os
import sys
import shutil
import uuid
import zipfile
import tempfile
import time
import logging
import json

# 确保 /app 在 Python 路径中（Cloud Run 工作目录）
sys.path.insert(0, os.path.abspath(os.environ.get("PYTHONPATH_INSERT", "/app")))

# 解决macOS上的OpenMP库冲突和numpy兼容性问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
from typing import List
from urllib.parse import quote

from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from semoPDFwatermark import PDFWatermarker
from company_matrix.company_matrix_routes import company_matrix_router

# ========== 应用配置 ==========
APP_VERSION = "1.1"  # 总体应用版本
APP_TITLE = "PDF水印添加工具"

# 各模块版本
PDF_WATERMARK_VERSION = "1.1.3"
COMPANY_MATRIX_VERSION = "1.0.1"

# 默认配置
DEFAULT_CONFIG = {
    "pagesize": "letter",
    "fontname": "Helvetica", 
    "fontsize": 60,
    "opacity": 0.3,
    "angle": 45,
    "color": "0,0,0"
}

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("pdf_watermark_app")

# ========== 应用初始化 ==========
def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""
    app = FastAPI(title=APP_TITLE, version=APP_VERSION)
    
    # 创建必要的目录
    for directory in ["static", "uploads", "results"]:
        os.makedirs(directory, exist_ok=True)
    
    # 设置静态文件和模板
    app.mount("/static", StaticFiles(directory="static"), name="static")
    # CAB题目图片静态文件服务
    if os.path.exists("question-images"):
        app.mount("/question-images", StaticFiles(directory="question-images"), name="question-images")
    
    # 包含路由
    app.include_router(company_matrix_router, prefix="/company-matrix", tags=["company-matrix"])
    
    return app

# 创建应用实例
app = create_app()
templates = Jinja2Templates(directory="templates")

# ========== 工具函数 ==========
def _parse_color_parameter(color: str) -> tuple:
    """解析颜色参数"""
    try:
        color_tuple = tuple(float(c) for c in color.split(','))
        if len(color_tuple) != 3:
            raise ValueError("颜色参数必须是3个由逗号分隔的数字")
        return color_tuple
    except ValueError:
        return None

def _create_session_directory() -> str:
    """创建会话目录"""
    session_id = str(uuid.uuid4())
    session_dir = os.path.join("results", session_id)
    os.makedirs(session_dir, exist_ok=True)
    logger.info(f"创建会话目录: {session_dir}")
    return session_id

async def _save_uploaded_files(files: List[UploadFile]) -> List[dict]:
    """保存上传的文件到临时目录"""
    temp_files = []
    for i, file in enumerate(files):
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"跳过非PDF文件: {file.filename}")
            continue
        
        try:
            content = await file.read()
            if not content:
                logger.warning(f"文件内容为空: {file.filename}")
                continue
            
            temp_fd, file_path = tempfile.mkstemp(suffix='.pdf', prefix=f'upload_{i}_')
            os.close(temp_fd)
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            actual_size = os.path.getsize(file_path)
            if actual_size == 0:
                logger.error(f"临时文件为空: {file_path}")
                continue
            
            logger.info(f"保存到临时文件: {file_path}, 大小: {actual_size} 字节")
            temp_files.append({
                "file_path": file_path,
                "filename": file.filename,
                "size": len(content)
            })
        except Exception as e:
            logger.error(f"读取或保存文件时出错: {file.filename}, {str(e)}")
            continue
    
    return temp_files

def _cleanup_temp_files(temp_files: List[str]):
    """清理临时文件"""
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"删除临时文件: {file_path}")
        except Exception as e:
            logger.error(f"删除临时文件出错: {file_path}, {str(e)}")

def _save_session_config(session_dir: str, config: dict):
    """保存会话配置到文件"""
    config_path = os.path.join(session_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"保存配置到: {config_path}")

# ========== 路由处理器 ==========


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页 - 工具集展示"""
    logger.info(f"Home page - PDF version: {PDF_WATERMARK_VERSION}, Company version: {COMPANY_MATRIX_VERSION}")
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "version": APP_VERSION,
        "pdf_version": PDF_WATERMARK_VERSION,
        "company_version": COMPANY_MATRIX_VERSION
    })


@app.get("/pdf-watermark", response_class=HTMLResponse)
async def pdf_watermark_page(request: Request):
    """PDF水印工具页面"""
    return templates.TemplateResponse("index.html", {"request": request, "version": PDF_WATERMARK_VERSION})


@app.get("/cab", response_class=HTMLResponse)
async def cab_page(request: Request):
    """CAB应用页面"""
    return templates.TemplateResponse("cab.html", {"request": request})


@app.post("/cab/upload-image")
async def upload_image_for_matching(
    request: Request,
    image: UploadFile = File(...)
):
    """
    CAB图片上传和相似度匹配接口
    """
    logger.info(f"CAB: Received image upload request - {image.filename}")
    
    # 验证文件类型
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    try:
        # 动态导入CAB模块
        try:
            from cab.feature_extractor import ImageFeatureExtractor
            from cab.image_index import ImageIndex
        except ImportError as e:
            logger.error(f"CAB modules not available: {e}")
            raise HTTPException(
                status_code=500, 
                detail="图像匹配功能暂不可用，请检查依赖安装"
            )
        
        # 读取上传的图片
        image_content = await image.read()
        if not image_content:
            raise HTTPException(status_code=400, detail="图片文件为空")
        
        # 保存临时文件
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='cab_upload_')
        os.close(temp_fd)
        
        try:
            with open(temp_path, "wb") as f:
                f.write(image_content)
            
            # 初始化特征提取器和索引
            extractor = ImageFeatureExtractor()
            index = ImageIndex()
            
            # 检查索引是否为空
            stats = index.get_stats()
            if stats['total_images'] == 0:
                return JSONResponse({
                    "success": False,
                    "message": "题目库为空，请先建立索引",
                    "matches": [],
                    "stats": stats
                })
            
            # 提取查询图片特征
            query_features = extractor.extract_features(temp_path)
            if query_features is None:
                raise HTTPException(status_code=400, detail="无法提取图片特征，请检查图片格式")
            
            # 搜索相似图片
            matches = index.search_similar(query_features, top_k=5)
            
            logger.info(f"CAB: Found {len(matches)} matches for uploaded image")
            
            return JSONResponse({
                "success": True,
                "message": f"成功找到 {len(matches)} 个匹配结果",
                "matches": matches,
                "stats": stats
            })
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("CAB: Error processing image upload")
        raise HTTPException(status_code=500, detail=f"处理图片时出错: {str(e)}")


@app.post("/cab/rebuild-index")
async def rebuild_image_index(request: Request):
    """
    重建图像索引接口
    """
    logger.info("CAB: Starting index rebuild request")
    
    try:
        # 动态导入CAB模块
        try:
            from cab.image_index import ImageIndex
        except ImportError as e:
            logger.error(f"CAB modules not available: {e}")
            raise HTTPException(
                status_code=500, 
                detail="图像索引功能暂不可用，请检查依赖安装"
            )
        
        # 初始化索引
        index = ImageIndex()
        
        # 重建索引
        success_count, total_count = index.rebuild_index()
        
        # 获取统计信息
        stats = index.get_stats()
        
        logger.info(f"CAB: Index rebuild completed - {success_count}/{total_count}")
        
        return JSONResponse({
            "success": True,
            "message": f"索引重建完成，成功处理 {success_count}/{total_count} 张图片",
            "success_count": success_count,
            "total_count": total_count,
            "stats": stats
        })
        
    except Exception as e:
        logger.exception("CAB: Error rebuilding index")
        raise HTTPException(status_code=500, detail=f"重建索引时出错: {str(e)}")


@app.get("/cab/stats")
async def get_index_stats(request: Request):
    """
    获取索引统计信息接口
    """
    try:
        # 动态导入CAB模块
        try:
            from cab.image_index import ImageIndex
        except ImportError as e:
            logger.error(f"CAB modules not available: {e}")
            return JSONResponse({
                "success": False,
                "message": "图像索引功能暂不可用，请安装相关依赖",
                "stats": {}
            })
        
        # 获取统计信息
        index = ImageIndex()
        stats = index.get_stats()
        
        return JSONResponse({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.exception("CAB: Error getting index stats")
        return JSONResponse({
            "success": False,
            "message": f"获取统计信息时出错: {str(e)}",
            "stats": {}
        })


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
            {"request": request, "error": "请选择至少一个PDF文件", "version": PDF_WATERMARK_VERSION}
        )
    
    # 验证和解析颜色参数
    color_tuple = _parse_color_parameter(color)
    if color_tuple is None:
        logger.error(f"颜色格式错误: {color}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": f"颜色格式错误: {color}", "version": PDF_WATERMARK_VERSION}
        )
    
    # 创建会话目录
    session_id = _create_session_directory()
    session_dir = os.path.join("results", session_id)
    
    # 保存上传的文件
    result_files = []
    
    try:
        # 预处理所有文件
        temp_files = await _save_uploaded_files(files)
        saved_files = [f["file_path"] for f in temp_files]
        
        logger.info(f"预处理完成，有效PDF文件: {len(temp_files)} 个")
        
        # 初始化水印器
        watermarker = PDFWatermarker()
        watermarker.set_pagesize(pagesize)
        
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
            {"request": request, "error": f"处理文件时出错: {str(e)}", "version": PDF_WATERMARK_VERSION}
        )
    
    finally:
        # 处理完成后删除临时文件
        _cleanup_temp_files(saved_files)
    
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
                {"request": request, "error": "所有PDF文件都是加密的，无法处理", "version": PDF_WATERMARK_VERSION}
            )
        else:
            logger.warning("没有找到有效的PDF文件进行处理")
            return templates.TemplateResponse(
                "index.html", 
                {"request": request, "error": "没有找到有效的PDF文件进行处理", "version": PDF_WATERMARK_VERSION}
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
    _save_session_config(session_dir, config)
    
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
            "version": PDF_WATERMARK_VERSION,
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
            {"request": request, "error": "配置信息不存在，无法重新生成", "version": PDF_WATERMARK_VERSION}
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
            "version": PDF_WATERMARK_VERSION
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