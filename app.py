import os
import shutil
import uuid
import zipfile
from typing import List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from semoPDFwatermark import PDFWatermarker

# 创建应用
app = FastAPI(title="PDF水印添加工具")

# 创建必要的目录
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# 设置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


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
    print(f"收到 {len(files)} 个文件")
    if not files:
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": "请选择至少一个PDF文件"}
        )
    
    # 处理颜色参数
    try:
        color_tuple = tuple(float(c) for c in color.split(','))
        if len(color_tuple) != 3:
            raise ValueError("颜色参数必须是3个由逗号分隔的数字")
    except ValueError as e:
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": f"颜色格式错误: {str(e)}"}
        )
    
    # 创建一个会话ID用于保存文件
    session_id = str(uuid.uuid4())
    session_dir = os.path.join("results", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # 保存上传的文件
    saved_files = []
    result_files = []
    
    try:
        watermarker = PDFWatermarker()
        watermarker.set_pagesize(pagesize)
        
        for i, file in enumerate(files):
            if not file.filename.lower().endswith('.pdf'):
                print(f"跳过非PDF文件: {file.filename}")
                continue
            
            # 先读取所有文件内容到内存
            content = await file.read()
            if not content:
                print(f"文件内容为空: {file.filename}")
                continue
                
            # 保存上传的文件
            file_path = os.path.join("uploads", f"{session_id}_{i}_{file.filename}")
            
            # 保存到磁盘
            with open(file_path, "wb") as f:
                f.write(content)
                
            saved_files.append(file_path)
            print(f"保存文件: {file_path}, 大小: {len(content)} 字节")
            
            # 添加水印
            output_filename = f"watermarked_{file.filename}"
            output_path = os.path.join(session_dir, output_filename)
            
            try:
                watermarker.add_watermark(
                    file_path,
                    watermark_text,
                    output_path,
                    fontname=fontname,
                    fontsize=fontsize,
                    opacity=opacity,
                    angle=angle,
                    color=color_tuple
                )
                
                print(f"处理完成: {output_path}")
                
                result_files.append({
                    "original": file.filename,
                    "processed": output_filename,
                    "download_url": f"/download/{session_id}/{output_filename}"
                })
            except Exception as e:
                print(f"处理文件 {file.filename} 时出错: {str(e)}")
    
    except Exception as e:
        # 清理会话文件
        for file in saved_files:
            if os.path.exists(file):
                os.remove(file)
        
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            
        print(f"处理出错: {str(e)}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": f"处理文件时出错: {str(e)}"}
        )
    
    # 处理完成后删除上传的文件
    for file in saved_files:
        if os.path.exists(file):
            os.remove(file)
    
    print(f"成功处理 {len(result_files)} 个文件")
    
    # 如果没有成功处理任何文件，返回错误
    if not result_files:
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": "没有找到有效的PDF文件进行处理"}
        )
    
    return templates.TemplateResponse(
        "result.html", 
        {
            "request": request, 
            "results": result_files,
            "session_id": session_id
        }
    )


@app.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """下载处理后的文件"""
    file_path = os.path.join("results", session_id, filename)
    if not os.path.exists(file_path):
        return {"error": "文件不存在"}
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
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
            if os.path.isfile(file_path):
                zipf.write(file_path, arcname=file)
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 