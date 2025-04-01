#!/usr/bin/env python3
import os
import unittest
import tempfile
from PyPDF2 import PdfReader
from semoPDFwatermark import PDFWatermarker


class TestPDFWatermarker(unittest.TestCase):
    """测试PDFWatermarker类"""
    
    def setUp(self):
        """测试前的准备工作，创建一个临时PDF文件"""
        self.watermarker = PDFWatermarker()
        
        # 创建测试用的临时PDF文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_pdf = os.path.join(self.temp_dir.name, "sample.pdf")
        
        # 使用reportlab创建一个简单的测试PDF
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(self.sample_pdf, pagesize=letter)
        c.drawString(100, 750, "测试PDF文件，第1页")
        c.showPage()  # 添加第一页
        
        c.drawString(100, 750, "测试PDF文件，第2页")
        c.showPage()  # 添加第二页
        
        c.save()
    
    def tearDown(self):
        """测试后的清理工作"""
        self.temp_dir.cleanup()
    
    def test_create_watermark(self):
        """测试创建水印功能"""
        watermark_buffer = self.watermarker.create_watermark("测试水印")
        
        # 检查生成的水印是否为有效的PDF
        watermark_pdf = PdfReader(watermark_buffer)
        self.assertEqual(len(watermark_pdf.pages), 1)
    
    def test_add_watermark_default_output(self):
        """测试添加水印功能，使用默认输出路径"""
        watermark_text = "测试水印"
        output_path = self.watermarker.add_watermark(self.sample_pdf, watermark_text)
        
        # 验证输出文件存在
        self.assertTrue(os.path.exists(output_path))
        
        # 验证输出文件是有效的PDF
        output_pdf = PdfReader(output_path)
        self.assertEqual(len(output_pdf.pages), 2)  # 应该仍然有2页
    
    def test_add_watermark_custom_output(self):
        """测试添加水印功能，使用自定义输出路径"""
        watermark_text = "测试水印"
        custom_output = os.path.join(self.temp_dir.name, "output.pdf")
        
        output_path = self.watermarker.add_watermark(
            self.sample_pdf, 
            watermark_text,
            custom_output
        )
        
        # 验证输出路径是否正确
        self.assertEqual(output_path, custom_output)
        
        # 验证输出文件存在
        self.assertTrue(os.path.exists(output_path))
    
    def test_custom_options(self):
        """测试自定义选项"""
        watermark_text = "测试水印"
        custom_output = os.path.join(self.temp_dir.name, "custom.pdf")
        
        output_path = self.watermarker.add_watermark(
            self.sample_pdf, 
            watermark_text,
            custom_output,
            fontname="Courier",
            fontsize=40,
            opacity=0.5,
            angle=30,
            color=(1, 0, 0)  # 红色
        )
        
        # 验证输出文件存在
        self.assertTrue(os.path.exists(output_path))
    
    def test_invalid_input_path(self):
        """测试无效的输入路径"""
        with self.assertRaises(FileNotFoundError):
            self.watermarker.add_watermark(
                "non_existent_file.pdf", 
                "测试水印"
            )


if __name__ == "__main__":
    unittest.main() 