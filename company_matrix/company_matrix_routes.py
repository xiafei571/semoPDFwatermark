from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

# 创建独立的路由
company_matrix_router = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory="templates")

@company_matrix_router.get("/", response_class=HTMLResponse)
async def company_matrix_page(request: Request):
    """公司矩阵生成页面"""
    return templates.TemplateResponse("company_matrix.html", {"request": request})

@company_matrix_router.post("/generate", response_class=HTMLResponse)
async def generate_company_matrix(
    request: Request,
    company_names: str = Form(...),
    rows: int = Form(...),
    cols: int = Form(...)
):
    """生成公司矩阵"""
    # 解析公司名称列表
    companies = [name.strip() for name in company_names.split('\n') if name.strip()]
    
    # 生成矩阵数据
    matrix_data = []
    for i in range(rows):
        row = []
        for j in range(cols):
            index = i * cols + j
            if index < len(companies):
                company_name = companies[index]
                # 生成域名（简单处理，实际可能需要更复杂的逻辑）
                domain = company_name.lower().replace(' ', '').replace('.', '') + '.com'
                row.append({
                    'name': company_name,
                    'domain': domain,
                    'logo_url': f"https://logo.clearbit.com/{domain}",
                    'website_url': f"https://www.{domain}"
                })
            else:
                row.append(None)
        matrix_data.append(row)
    
    return templates.TemplateResponse("company_matrix_result.html", {
        "request": request,
        "matrix_data": matrix_data,
        "rows": rows,
        "cols": cols,
        "total_companies": len(companies)
    })

@company_matrix_router.post("/generate-json")
async def generate_company_matrix_json(
    company_names: str = Form(...),
    rows: int = Form(...),
    cols: int = Form(...)
):
    """生成公司矩阵JSON数据"""
    # 解析公司名称列表
    companies = [name.strip() for name in company_names.split('\n') if name.strip()]
    
    # 生成矩阵数据
    matrix_data = []
    for i in range(rows):
        row = []
        for j in range(cols):
            index = i * cols + j
            if index < len(companies):
                company_name = companies[index]
                # 生成域名（简单处理，实际可能需要更复杂的逻辑）
                domain = company_name.lower().replace(' ', '').replace('.', '') + '.com'
                row.append({
                    'name': company_name,
                    'domain': domain,
                    'logo_url': f"https://logo.clearbit.com/{domain}",
                    'website_url': f"https://www.{domain}"
                })
            else:
                row.append(None)
        matrix_data.append(row)
    
    return JSONResponse({
        "matrix_data": matrix_data,
        "rows": rows,
        "cols": cols,
        "total_companies": len(companies)
    }) 