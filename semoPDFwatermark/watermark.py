#!/usr/bin/env python3
import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import platform

# 根据操作系统注册中文字体
def register_chinese_font():
    """注册中文字体，根据不同操作系统选择适合的字体"""
    # Docker/Linux环境常用的中文字体路径
    docker_fonts = [
        # WenQuanYi Micro Hei
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        # WenQuanYi Zen Hei
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        # Noto Sans CJK
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    
    # 先检查Docker/Linux环境字体
    for font_path in docker_fonts:
        if os.path.exists(font_path):
            font_name = os.path.basename(font_path).split('.')[0].replace("-", "")
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"成功注册中文字体: {font_name} ({font_path})")
                return font_name
            except Exception as e:
                print(f"注册字体失败 {font_path}: {e}")
    
    # 其他操作系统字体检测
    system = platform.system()
    font_path = None
    font_name = "SimSun"  # 默认字体名称
    
    if system == "Windows":
        # Windows 系统的中文字体路径
        font_path = "C:\\Windows\\Fonts\\simsun.ttc"
    elif system == "Darwin":  # macOS
        # macOS 系统的中文字体路径
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # PingFang 字体
            "/Library/Fonts/Arial Unicode.ttf",    # Arial Unicode
            "/System/Library/Fonts/STHeiti Light.ttc", # 华文细黑
            "/System/Library/Fonts/Hiragino Sans GB.ttc" # 冬青黑体
        ]
        for path in font_paths:
            if os.path.exists(path):
                font_path = path
                font_name = os.path.basename(path).split('.')[0].replace(" ", "")
                break
    elif system == "Linux":
        # Linux 系统的中文字体路径
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
            "/usr/share/fonts/truetype/arphic/uming.ttc"      # AR PL UMing
        ]
        for path in font_paths:
            if os.path.exists(path):
                font_path = path
                font_name = os.path.basename(path).split('.')[0].replace(" ", "")
                break
    
    # 注册字体
    if font_path and os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            print(f"成功注册中文字体: {font_name} ({font_path})")
            return font_name
        except Exception as e:
            print(f"注册字体失败: {e}")
            
    # 尝试使用已注册的字体
    try:
        # 以下是ReportLab内置的支持中文的字体
        pdfmetrics.registerFont(TTFont('STSong-Light', 'STSong-Light', 'UniGB-UCS2-H'))
        return 'STSong-Light'
    except:
        pass
    
    print("无法找到合适的中文字体，将使用默认字体")
    return None  # 如果无法找到合适的中文字体，返回None


class PDFWatermarker:
    """PDF水印处理类，提供更多的自定义选项"""
    
    def __init__(self):
        self.pagesize = letter  # 默认页面大小
        self.chinese_font = register_chinese_font()  # 注册并获取中文字体
    
    def set_pagesize(self, size_name):
        """
        设置页面大小
        
        Args:
            size_name: 页面大小名称 ('letter' 或 'A4')
        """
        if size_name.lower() == 'a4':
            self.pagesize = A4
        else:
            self.pagesize = letter
    
    def create_watermark(self, text, fontname="Helvetica", fontsize=60, 
                         opacity=0.3, angle=45, color=(0, 0, 0)):
        """
        创建水印
        
        Args:
            text: 水印文本
            fontname: 字体名称
            fontsize: 字体大小
            opacity: 不透明度 (0-1)
            angle: 水印旋转角度
            color: RGB颜色元组 (r, g, b)，取值范围 0-1
            
        Returns:
            BytesIO: 包含水印的内存缓冲区
        """
        # 创建内存缓冲区
        packet = io.BytesIO()
        
        # 创建一个新的PDF
        c = canvas.Canvas(packet, pagesize=self.pagesize)
        
        # 检查文本是否包含中文字符
        has_chinese = False
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                has_chinese = True
                break
        
        # 如果有中文字符且注册了中文字体，则使用中文字体
        if has_chinese and self.chinese_font:
            fontname = self.chinese_font
            print(f"检测到中文文本，使用字体: {fontname}")
        
        # 设置字体和大小
        try:
            c.setFont(fontname, fontsize)
        except Exception as e:
            print(f"设置字体 {fontname} 失败: {e}, 将使用默认字体")
            c.setFont("Helvetica", fontsize)  # 使用默认字体
        
        # 设置颜色和透明度
        r, g, b = color
        c.setFillColor(Color(r, g, b, alpha=opacity))
        
        # 保存当前状态
        c.saveState()
        
        # 旋转画布
        width, height = self.pagesize
        c.translate(width/2, height/2)
        c.rotate(angle)
        
        # 绘制水印文本
        c.drawCentredString(0, 0, text)
        
        # 恢复状态
        c.restoreState()
        
        # 保存PDF
        c.save()
        
        # 将缓冲区移动到开始位置
        packet.seek(0)
        return packet
    
    def add_watermark(self, input_pdf_path, watermark_text, output_pdf_path=None, 
                      fontname="Helvetica", fontsize=60, opacity=0.3, 
                      angle=45, color=(0, 0, 0)):
        """
        给PDF添加水印
        
        Args:
            input_pdf_path: 输入PDF文件路径
            watermark_text: 水印文本
            output_pdf_path: 输出PDF文件路径，默认为在原文件名后加上"_watermarked"
            fontname: 字体名称
            fontsize: 字体大小
            opacity: 不透明度 (0-1)
            angle: 水印旋转角度
            color: RGB颜色元组 (r, g, b)，取值范围 0-1
            
        Returns:
            str: 输出文件路径
        """
        if not os.path.exists(input_pdf_path):
            raise FileNotFoundError(f"PDF文件 {input_pdf_path} 不存在")
        
        # 创建默认输出路径（如果未提供）
        if output_pdf_path is None:
            file_name, file_ext = os.path.splitext(input_pdf_path)
            output_pdf_path = f"{file_name}_watermarked{file_ext}"
        
        # 创建水印
        watermark_buffer = self.create_watermark(
            watermark_text, fontname, fontsize, opacity, angle, color
        )
        watermark_pdf = PdfReader(watermark_buffer)
        watermark_page = watermark_pdf.pages[0]
        
        # 打开要添加水印的PDF
        pdf_reader = PdfReader(input_pdf_path)
        pdf_writer = PdfWriter()
        
        # 将水印添加到每一页
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page.merge_page(watermark_page)
            pdf_writer.add_page(page)
        
        # 保存输出文件
        with open(output_pdf_path, "wb") as output_file:
            pdf_writer.write(output_file)
        
        return output_pdf_path 