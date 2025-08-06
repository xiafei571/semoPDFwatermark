# PDF水印添加工具 & 公司矩阵生成器

一个多功能Python工具集，包含PDF水印添加工具和公司矩阵生成器。提供命令行工具和Web界面两种使用方式。

## 功能特点

### PDF水印工具
- 给PDF文件的每一页添加文本水印
- 自定义水印文本、字体、大小、颜色、透明度和角度
- 支持Letter和A4页面大小
- 支持中文水印文本
- 提供简单的命令行界面
- 提供Web界面，支持批量上传和处理
- Docker容器化部署
- 提供可重用的Python模块

### 公司矩阵生成器
- 自动生成公司矩阵展示页面
- 智能公司名称自动完成功能
- 预定义25+知名公司数据
- 自动获取公司Logo和网站链接
- 支持自定义矩阵大小（M×N）
- 实时预览矩阵布局
- 一键下载HTML文件
- 响应式设计，适配各种屏幕

## 安装

### 命令行工具

1. 克隆此仓库:
   ```
   git clone https://github.com/xiafei571/semoPDFwatermark.git
   cd semoPDFwatermark
   ```

2. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

### Web应用

1. 安装Web应用依赖:
   ```
   pip install -r requirements_web.txt
   ```

2. 运行应用:
   ```
   python app.py
   ```

3. 访问 http://localhost:8000 使用Web界面

### Docker部署

1. 使用Docker Compose启动:
   ```
   docker-compose up -d
   ```

2. 访问 http://localhost:8000 使用Web界面

## 使用方法

### 命令行使用

基本用法:

```bash
python -m semoPDFwatermark.cli "input.pdf" "机密文件"
```

这将在原PDF的每一页添加"机密文件"的水印，并生成一个名为"input_watermarked.pdf"的文件。

高级用法:

```bash
python -m semoPDFwatermark.cli "input.pdf" "CONFIDENTIAL" --pagesize a4 --fontsize 72 --opacity 0.5 --angle 30 --color 1,0,0 -o output.pdf
```

这将添加红色(1,0,0)的"CONFIDENTIAL"水印，字体大小为72，不透明度为0.5，旋转角度为30度，并保存为output.pdf。

### 批量处理命令行

```bash
python -m semoPDFwatermark.batch_watermark "*.pdf" "DRAFT" --output-dir ./watermarked --opacity 0.1
```

这将处理当前目录下的所有PDF文件，添加"DRAFT"水印，不透明度为0.1，并将结果保存到watermarked目录。

### Web界面使用

#### PDF水印工具
1. 访问 http://localhost:8000
2. 上传一个或多个PDF文件
3. 输入水印文本和选择水印选项
4. 点击"添加水印"按钮
5. 下载处理后的文件

#### 公司矩阵生成器
1. 访问 http://localhost:8000/company-matrix
2. 使用自动完成功能搜索并添加公司名称
3. 选择矩阵大小（行数和列数）
4. 点击"生成矩阵"按钮
5. 预览结果并下载HTML文件

### 编程方式使用

您也可以在自己的Python代码中导入并使用PDFWatermarker类:

```python
from semoPDFwatermark import PDFWatermarker

watermarker = PDFWatermarker()
watermarker.set_pagesize('a4')
watermarker.add_watermark(
    'input.pdf',
    'DRAFT',
    output_pdf_path='output.pdf',
    fontsize=50,
    opacity=0.4,
    angle=30,
    color=(0.5, 0, 0)
)
```

## 参数说明

- `pdf_path`: 输入PDF文件路径（必需）
- `watermark_text`: 水印文本（必需）
- `-o, --output`: 输出PDF文件路径（可选，默认为在原文件名后加上"_watermarked"）
- `--pagesize`: 页面大小，可选值为"letter"或"a4"（默认为"letter"）
- `--fontname`: 字体名称（默认为"Helvetica"）
- `--fontsize`: 字体大小（默认为60）
- `--opacity`: 不透明度，取值范围0-1（默认为0.3）
- `--angle`: 水印旋转角度（默认为45度）
- `--color`: RGB颜色，格式为"r,g,b"，取值范围0-1（默认为黑色"0,0,0"）

## 中文支持

程序会自动检测水印文本中的中文字符，并尝试使用系统中安装的中文字体。支持Windows、macOS和Linux系统。

## 依赖

- PyPDF2
- reportlab
- FastAPI (Web应用)
- uvicorn (Web应用)
- Jinja2 (Web应用)

## 许可证

MIT 