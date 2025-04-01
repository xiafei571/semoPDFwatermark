#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="semoPDFwatermark",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="给PDF文件添加水印的Python工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/semoPDFwatermark",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.6",
    install_requires=[
        "PyPDF2>=2.0.0",
        "reportlab>=3.6.0",
    ],
    entry_points={
        "console_scripts": [
            "pdfwatermark=semoPDFwatermark.cli:main",
            "pdfwatermark-batch=semoPDFwatermark.batch_watermark:main",
        ],
    },
) 