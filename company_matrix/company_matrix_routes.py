from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from .company_data import get_company_suggestions, get_company_by_name

# 版本配置
COMPANY_MATRIX_VERSION = "1.0.1"

# 创建独立的路由
company_matrix_router = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory="templates")

@company_matrix_router.get("/", response_class=HTMLResponse)
async def company_matrix_page(request: Request):
    """公司矩阵生成页面"""
    return templates.TemplateResponse("company_matrix.html", {"request": request, "version": COMPANY_MATRIX_VERSION})

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
                # 尝试从预定义数据中获取公司信息
                company_info = get_company_by_name(company_name)
                if company_info:
                    row.append({
                        'name': company_info['name'],
                        'domain': company_info['domain'],
                        'logo_url': f"https://logo.clearbit.com/{company_info['domain']}",
                        'website_url': company_info['website']
                    })
                else:
                    # 如果不在预定义列表中，使用默认逻辑
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
        "total_companies": len(companies),
        "version": COMPANY_MATRIX_VERSION
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
                # 尝试从预定义数据中获取公司信息
                company_info = get_company_by_name(company_name)
                if company_info:
                    row.append({
                        'name': company_info['name'],
                        'domain': company_info['domain'],
                        'logo_url': f"https://logo.clearbit.com/{company_info['domain']}",
                        'website_url': company_info['website']
                    })
                else:
                    # 如果不在预定义列表中，使用默认逻辑
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

@company_matrix_router.get("/autocomplete")
async def get_company_suggestions_api(query: str):
    """获取公司名称自动完成建议"""
    suggestions = get_company_suggestions(query)
    return JSONResponse({
        "suggestions": suggestions
    }) 