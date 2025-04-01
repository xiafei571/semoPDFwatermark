#!/usr/bin/env python3
import os
import argparse
import glob
from .watermark import PDFWatermarker


def batch_process(input_pattern, watermark_text, output_dir=None, **kwargs):
    """
    批量处理多个PDF文件
    
    Args:
        input_pattern: 输入文件的glob模式，如 "*.pdf" 或 "documents/*.pdf"
        watermark_text: 水印文本
        output_dir: 输出目录，如果不提供则使用原始文件目录
        **kwargs: 传递给 add_watermark 的其他参数
    
    Returns:
        list: 成功处理的文件列表
    """
    # 查找匹配的文件
    matching_files = glob.glob(input_pattern)
    
    if not matching_files:
        print(f"未找到匹配的文件: {input_pattern}")
        return []
    
    watermarker = PDFWatermarker()
    if kwargs.get('pagesize'):
        watermarker.set_pagesize(kwargs.pop('pagesize'))
    
    successful_files = []
    
    for input_file in matching_files:
        if not input_file.lower().endswith('.pdf'):
            print(f"跳过非PDF文件: {input_file}")
            continue
            
        # 确定输出路径
        if output_dir:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            file_name = os.path.basename(input_file)
            name, ext = os.path.splitext(file_name)
            output_file = os.path.join(output_dir, f"{name}_watermarked{ext}")
        else:
            output_file = None  # 使用默认命名
        
        try:
            output_path = watermarker.add_watermark(
                input_file, 
                watermark_text,
                output_file,
                **kwargs
            )
            successful_files.append(output_path)
            print(f"已处理: {input_file} -> {output_path}")
        except Exception as e:
            print(f"处理 {input_file} 时出错: {e}")
    
    return successful_files


def main():
    """批量处理命令行界面"""
    parser = argparse.ArgumentParser(description="批量为多个PDF文件添加水印")
    
    # 必要参数
    parser.add_argument("input_pattern", help="输入文件的glob模式，如 \"*.pdf\" 或 \"docs/*.pdf\"")
    parser.add_argument("watermark_text", help="水印文本")
    
    # 可选参数
    parser.add_argument("-o", "--output-dir", help="输出目录（可选）")
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
        
        # 提取参数为字典
        kwargs = {
            'pagesize': args.pagesize,
            'fontname': args.fontname,
            'fontsize': args.fontsize,
            'opacity': args.opacity,
            'angle': args.angle,
            'color': color
        }
        
        # 批量处理
        successful_files = batch_process(
            args.input_pattern,
            args.watermark_text,
            args.output_dir,
            **kwargs
        )
        
        # 输出总结
        if successful_files:
            print(f"\n成功处理 {len(successful_files)} 个文件:")
            for file in successful_files:
                print(f"- {file}")
        else:
            print("\n没有成功处理任何文件")
    
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main() 