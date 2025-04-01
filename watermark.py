#!/usr/bin/env python3
import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import Color


class PDFWatermarker:
    """PDF水印处理类，提供更多的自定义选项"""
    
    def __init__(self):
        self.pagesize = letter  # 默认页面大小
    
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
        
        # 设置字体和大小
        c.setFont(fontname, fontsize)
        
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