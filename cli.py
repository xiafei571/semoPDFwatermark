#!/usr/bin/env python3
import argparse
from watermark import PDFWatermarker


def main():
    """命令行界面主函数"""
    parser = argparse.ArgumentParser(description="给PDF文件的每一页添加水印")
    
    # 必要参数
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("watermark_text", help="水印文本")
    
    # 可选参数
    parser.add_argument("-o", "--output", help="输出PDF文件路径（可选）")
    parser.add_argument("--pagesize", choices=["letter", "a4"], default="letter", 
                      help="页面大小，默认为letter")
    parser.add_argument("--fontname", default="Helvetica", 
                      help="字体名称，默认为Helvetica")
    parser.add_argument("--fontsize", type=int, default=60, 
                      help="字体大小，默认为60")
    parser.add_argument("--opacity", type=float, default=0.3, 
                      help="不透明度 (0-1)，默认为0.3")
    parser.add_argument("--angle", type=float, default=45, 
                      help="水印旋转角度，默认为45度")
    parser.add_argument("--color", default="0,0,0", 
                      help="RGB颜色，格式为'r,g,b'，取值范围0-1，默认为黑色'0,0,0'")
    
    args = parser.parse_args()
    
    try:
        # 处理颜色参数
        color = tuple(float(c) for c in args.color.split(','))
        if len(color) != 3:
            raise ValueError("颜色参数必须是3个由逗号分隔的数字")
        
        # 创建水印处理器
        watermarker = PDFWatermarker()
        watermarker.set_pagesize(args.pagesize)
        
        # 添加水印
        output_path = watermarker.add_watermark(
            args.pdf_path, 
            args.watermark_text,
            args.output,
            args.fontname,
            args.fontsize,
            args.opacity,
            args.angle,
            color
        )
        
        print(f"水印已添加，文件已保存至: {output_path}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main() 