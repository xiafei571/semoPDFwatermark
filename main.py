#!/usr/bin/env python3
import os
import argparse
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
import io


def create_watermark(text, output_path):
    """
    创建水印PDF文件
    
    Args:
        text: 水印文本
        output_path: 临时水印文件路径
    """
    # 创建内存缓冲区
    packet = io.BytesIO()
    
    # 创建一个新的PDF，使用reportlab
    c = canvas.Canvas(packet, pagesize=letter)
    
    # 设置字体和大小
    c.setFont("Helvetica", 60)
    
    # 半透明灰色
    c.setFillColor(Color(0, 0, 0, alpha=0.3))
    
    # 保存当前状态
    c.saveState()
    
    # 旋转画布
    c.translate(letter[0]/2, letter[1]/2)
    c.rotate(45)
    
    # 绘制水印文本
    c.drawCentredString(0, 0, text)
    
    # 恢复状态
    c.restoreState()
    
    # 保存PDF
    c.save()
    
    # 将缓冲区移动到开始位置
    packet.seek(0)
    return packet


def add_watermark(input_pdf_path, watermark_text, output_pdf_path=None):
    """
    给PDF添加水印
    
    Args:
        input_pdf_path: 输入PDF文件路径
        watermark_text: 水印文本
        output_pdf_path: 输出PDF文件路径，默认为在原文件名后加上"_watermarked"
    
    Returns:
        输出文件路径
    """
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"PDF文件 {input_pdf_path} 不存在")
    
    # 创建默认输出路径（如果未提供）
    if output_pdf_path is None:
        file_name, file_ext = os.path.splitext(input_pdf_path)
        output_pdf_path = f"{file_name}_watermarked{file_ext}"
    
    # 创建水印
    watermark_buffer = create_watermark(watermark_text, None)
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="给PDF文件的每一页添加水印")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("watermark_text", help="水印文本")
    parser.add_argument("-o", "--output", help="输出PDF文件路径（可选）")
    
    args = parser.parse_args()
    
    try:
        output_path = add_watermark(args.pdf_path, args.watermark_text, args.output)
        print(f"水印已添加，文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main() 