#!/usr/bin/env python3
"""
示例脚本，展示如何使用semoPDFwatermark库

这个脚本展示了：
1. 基本用法
2. 高级选项用法
3. 批量处理多个PDF文件

注意：这个脚本需要在当前目录下有test.pdf文件才能正常运行
"""

from semoPDFwatermark import PDFWatermarker
from semoPDFwatermark.batch_watermark import batch_process
import os


def basic_usage():
    """基本用法示例"""
    print("="*50)
    print("基本用法示例")
    print("="*50)
    
    watermarker = PDFWatermarker()
    
    # 检查测试文件是否存在
    if not os.path.exists("test.pdf"):
        print("错误: 示例需要在当前目录下有test.pdf文件")
        return
    
    # 添加默认水印
    output_path = watermarker.add_watermark(
        "test.pdf", 
        "CONFIDENTIAL"
    )
    
    print(f"已添加默认水印，文件保存为: {output_path}")
    print()


def advanced_usage():
    """高级选项用法示例"""
    print("="*50)
    print("高级选项用法示例")
    print("="*50)
    
    watermarker = PDFWatermarker()
    
    # 检查测试文件是否存在
    if not os.path.exists("test.pdf"):
        print("错误: 示例需要在当前目录下有test.pdf文件")
        return
    
    # 设置页面大小为A4
    watermarker.set_pagesize("a4")
    
    # 添加自定义水印
    output_path = watermarker.add_watermark(
        "test.pdf",
        "机密文件",
        "test_custom.pdf",  # 自定义输出路径
        fontname="Helvetica-Bold",  # 粗体
        fontsize=80,  # 更大的字体
        opacity=0.2,  # 更透明
        angle=30,  # 不同的角度
        color=(1, 0, 0)  # 红色
    )
    
    print(f"已添加自定义水印，文件保存为: {output_path}")
    print()


def batch_processing():
    """批量处理示例"""
    print("="*50)
    print("批量处理示例")
    print("="*50)
    
    # 检查测试目录是否存在
    if not os.path.exists("pdfs"):
        os.makedirs("pdfs")
        print("已创建'pdfs'目录，请在目录中放入PDF文件后再运行此示例")
        return
    
    # 获取目录中的PDF文件数量
    pdf_files = [f for f in os.listdir("pdfs") if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("'pdfs'目录中没有PDF文件，请添加一些PDF文件后再运行此示例")
        return
    
    # 创建输出目录
    if not os.path.exists("output"):
        os.makedirs("output")
    
    # 批量处理
    successful_files = batch_process(
        "pdfs/*.pdf",  # 输入模式
        "DRAFT",  # 水印文本
        "output",  # 输出目录
        fontsize=70,
        opacity=0.4,
        angle=45,
        color=(0, 0, 0.8)  # 蓝色
    )
    
    # 输出结果
    if successful_files:
        print(f"\n成功处理 {len(successful_files)} 个文件:")
        for file in successful_files:
            print(f"- {file}")
    else:
        print("\n没有成功处理任何文件")


if __name__ == "__main__":
    print("semoPDFwatermark 示例脚本")
    print("="*50)
    
    basic_usage()
    advanced_usage()
    batch_processing()
    
    print("\n示例运行完成!") 