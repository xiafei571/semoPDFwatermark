import os
import io
import logging
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFWatermarker:
    def __init__(self):
        """初始化水印器"""
        self.pagesize = (8.5 * inch, 11 * inch)  # 默认为letter大小
    
    def set_pagesize(self, size_name):
        """设置页面大小"""
        if size_name.lower() == 'a4':
            self.pagesize = (210 * mm, 297 * mm)
        else:  # 默认为letter
            self.pagesize = (8.5 * inch, 11 * inch)
        
        logger.info(f"设置页面大小为: {size_name}")
        return self
    
    def _is_chinese(self, text):
        """检查文本是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def create_watermark(self, text, output_path=None, fontname='Helvetica', fontsize=60, 
                         opacity=0.3, angle=45, color=(0, 0, 0)):
        """
        创建水印
        
        参数:
            text: 水印文本
            output_path: 输出路径，如果为None则返回内存中的PDF内容
            fontname: 字体名称
            fontsize: 字体大小
            opacity: 不透明度 (0-1)
            angle: 旋转角度
            color: RGB颜色元组，值范围0-1
        
        返回:
            如果output_path为None，返回内存中的PDF内容，否则保存到output_path并返回True
        """
        try:
            # 创建水印画布
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=self.pagesize)
            width, height = self.pagesize
            
            # 设置透明度和颜色
            c.setFillColorRGB(*color)
            c.setFillAlpha(opacity)
            
            # 设置字体
            try:
                c.setFont(fontname, fontsize)
            except Exception as e:
                logger.error(f"设置字体 {fontname} 失败: {str(e)}")
                # 如果字体设置失败，尝试使用默认字体
                c.setFont('Helvetica', fontsize)
            
            # 在页面中心添加旋转的文本
            c.saveState()
            c.translate(width/2, height/2)
            c.rotate(angle)
            
            # 计算文本宽度以居中绘制
            text_width = c.stringWidth(text, fontname, fontsize)
            c.drawString(-text_width/2, 0, text)
            
            c.restoreState()
            c.save()
            
            # 获取PDF内容
            packet.seek(0)
            
            if output_path:
                # 将内存中的内容保存到文件
                with open(output_path, 'wb') as f:
                    f.write(packet.getvalue())
                return True
            else:
                return packet.getvalue()
                
        except Exception as e:
            logger.error(f"创建水印时出错: {str(e)}")
            return None
    
    def add_watermark(self, input_pdf, watermark_text, output_pdf, fontname='Helvetica', 
                      fontsize=60, opacity=0.3, angle=45, color=(0, 0, 0)):
        """
        向PDF文件添加水印
        
        参数:
            input_pdf: 输入PDF文件路径
            watermark_text: 水印文本
            output_pdf: 输出PDF文件路径
            fontname: 字体名称
            fontsize: 字体大小
            opacity: 不透明度 (0-1)
            angle: 旋转角度
            color: RGB颜色元组，值范围0-1
        
        返回:
            成功返回True，失败返回False
        """
        if not os.path.exists(input_pdf):
            logger.error(f"输入文件不存在: {input_pdf}")
            return False
            
        if os.path.getsize(input_pdf) == 0:
            logger.error(f"输入文件为空: {input_pdf}")
            return False
        
        logger.info(f"开始处理文件: {input_pdf}")
        
        try:
            # 创建水印
            logger.info(f"创建水印文本: {watermark_text}")
            watermark_data = self.create_watermark(
                watermark_text, 
                fontname=fontname, 
                fontsize=fontsize, 
                opacity=opacity, 
                angle=angle, 
                color=color
            )
            
            if watermark_data is None:
                logger.error("无法创建水印")
                return False
            
            # 打开原始PDF
            logger.info(f"打开PDF文件: {input_pdf}")
            reader = None
            writer = None
            
            try:
                with open(input_pdf, 'rb') as f:
                    reader = PdfReader(f)
                    if len(reader.pages) == 0:
                        logger.error(f"PDF文件没有页面: {input_pdf}")
                        return False
                        
                    watermark_pdf = PdfReader(io.BytesIO(watermark_data))
                    if len(watermark_pdf.pages) == 0:
                        logger.error("水印PDF没有页面")
                        return False
                        
                    watermark_page = watermark_pdf.pages[0]
                    writer = PdfWriter()
                    
                    # 将水印添加到每一页
                    logger.info(f"添加水印到 {len(reader.pages)} 个页面")
                    for i in range(len(reader.pages)):
                        page = reader.pages[i]
                        page.merge_page(watermark_page)
                        writer.add_page(page)
                
                # 保存结果
                logger.info(f"保存添加水印后的文件: {output_pdf}")
                with open(output_pdf, 'wb') as out:
                    writer.write(out)
                
                # 验证输出
                if not os.path.exists(output_pdf):
                    logger.error(f"无法创建输出文件: {output_pdf}")
                    return False
                    
                if os.path.getsize(output_pdf) == 0:
                    logger.error(f"输出文件为空: {output_pdf}")
                    return False
                
                logger.info(f"成功添加水印到文件: {input_pdf} -> {output_pdf}")
                return True
                
            except Exception as e:
                logger.error(f"处理PDF时出错: {str(e)}")
                # 如果输出文件已经创建但可能不完整，尝试删除它
                if output_pdf and os.path.exists(output_pdf):
                    try:
                        os.remove(output_pdf)
                        logger.info(f"删除不完整的输出文件: {output_pdf}")
                    except Exception:
                        pass
                return False
                
        except Exception as e:
            logger.error(f"添加水印过程中出错: {str(e)}")
            return False 