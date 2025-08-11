#!/usr/bin/env python3
"""
CAB图像匹配系统管理工具
用于索引管理、数据维护等操作
"""

import os
import sys
import argparse
import logging
from typing import Optional
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """检查所需依赖是否已安装"""
    try:
        import torch
        import open_clip
        import faiss
        import pandas as pd
        from PIL import Image
        logger.info("All required dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install required packages:")
        logger.error("pip install -r cab_requirements.txt")
        return False

def rebuild_index(questions_csv: str = "questions.csv", images_dir: str = "question-images"):
    """重建图像索引"""
    if not check_dependencies():
        return False
    
    try:
        from cab.image_index import ImageIndex
        
        logger.info("Starting index rebuild...")
        index = ImageIndex()
        success_count, total_count = index.rebuild_index(questions_csv, images_dir)
        
        logger.info(f"Index rebuild completed: {success_count}/{total_count} images processed")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding index: {e}")
        return False

def show_stats():
    """显示索引统计信息"""
    if not check_dependencies():
        return False
    
    try:
        from cab.image_index import ImageIndex
        
        index = ImageIndex()
        stats = index.get_stats()
        
        print("\n=== CAB索引统计信息 ===")
        print(f"总图片数量: {stats['total_images']}")
        print(f"索引大小: {stats['index_size']}")
        print(f"特征维度: {stats['feature_dimension']}")
        print(f"索引文件存在: {'是' if stats['index_exists'] else '否'}")
        print(f"元数据文件存在: {'是' if stats['metadata_exists'] else '否'}")
        print("=" * 30)
        
        return True
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return False

def test_matching(image_path: str, top_k: int = 5):
    """测试图像匹配功能"""
    if not check_dependencies():
        return False
    
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return False
    
    try:
        from cab.feature_extractor import ImageFeatureExtractor
        from cab.image_index import ImageIndex
        
        logger.info(f"Testing image matching for: {image_path}")
        
        # 初始化组件
        extractor = ImageFeatureExtractor()
        index = ImageIndex()
        
        # 检查索引
        stats = index.get_stats()
        if stats['total_images'] == 0:
            logger.error("Index is empty. Please rebuild index first.")
            return False
        
        # 提取特征
        features = extractor.extract_features(image_path)
        if features is None:
            logger.error("Failed to extract features from image")
            return False
        
        # 搜索匹配
        matches = index.search_similar(features, top_k)

        # 计算校准后的置信度（在Top-K内部做温度Softmax，默认T=0.25）
        if matches:
            sims = np.array([m['similarity'] for m in matches], dtype=np.float32)
            temp = float(os.environ.get("CAB_SCORE_TEMP", 0.1))
            temp = max(1e-3, min(5.0, temp))
            # 数值稳定：先减最大值
            logits = sims - sims.max()
            probs = np.exp(logits / temp)
            probs = probs / (probs.sum() + 1e-12)
        else:
            probs = np.array([])
        
        print(f"\n=== 匹配结果 (Top {len(matches)}) ===")
        for i, match in enumerate(matches):
            cosine_percent = match['similarity'] * 100
            prob_percent = (probs[i] * 100) if probs.size else 0.0
            print(f"{i+1}. 文件: {match['filename']}")
            print(f"   余弦相似度: {cosine_percent:.1f}%  |  校准置信度: {prob_percent:.1f}% (T={float(os.environ.get('CAB_SCORE_TEMP', 0.25))})")
            print(f"   答案: {match['answer']}")
            print(f"   排名: #{match['rank']}")
            print("-" * 40)

        # 额外输出Top-1与Top-2的差距，帮助判断难度
        if len(matches) >= 2:
            margin = matches[0]['similarity'] - matches[1]['similarity']
            print(f"Top1-Top2 余弦相似度差距: {margin:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing matching: {e}")
        return False

def setup_sample_data():
    """设置示例数据"""
    logger.info("Setting up sample data...")
    
    # 创建示例CSV文件
    questions_csv = "questions.csv"
    if not os.path.exists(questions_csv):
        with open(questions_csv, 'w', encoding='utf-8') as f:
            f.write("filename,answer\n")
            f.write("sample_question_1.jpg,这是示例题目1的答案\n")
            f.write("sample_question_2.jpg,这是示例题目2的答案\n")
        logger.info(f"Created sample CSV: {questions_csv}")
    
    # 创建images目录
    images_dir = "question-images"
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        logger.info(f"Created images directory: {images_dir}")
        logger.info("Please add your question images to this directory")
    
    logger.info("Sample data setup completed")
    return True

def main():
    parser = argparse.ArgumentParser(description="CAB图像匹配系统管理工具")
    parser.add_argument('--action', choices=['rebuild', 'stats', 'test', 'setup'], 
                       required=True, help='要执行的操作')
    parser.add_argument('--questions-csv', default='questions.csv', 
                       help='问题数据CSV文件路径')
    parser.add_argument('--images-dir', default='question-images', 
                       help='图像目录路径')
    parser.add_argument('--test-image', help='用于测试的图像文件路径')
    parser.add_argument('--top-k', type=int, default=5, help='返回最相似的前K个结果')
    
    args = parser.parse_args()
    
    if args.action == 'setup':
        success = setup_sample_data()
    elif args.action == 'rebuild':
        success = rebuild_index(args.questions_csv, args.images_dir)
    elif args.action == 'stats':
        success = show_stats()
    elif args.action == 'test':
        if not args.test_image:
            logger.error("Please specify --test-image for testing")
            sys.exit(1)
        success = test_matching(args.test_image, args.top_k)
    else:
        logger.error(f"Unknown action: {args.action}")
        sys.exit(1)
    
    if success:
        logger.info("Operation completed successfully")
        sys.exit(0)
    else:
        logger.error("Operation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()