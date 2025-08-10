"""
图像索引管理模块
使用FAISS进行高效的相似度检索
"""

import os
import pickle
import numpy as np
import pandas as pd
import faiss
from typing import List, Tuple, Dict, Optional
import logging
from .feature_extractor import ImageFeatureExtractor

logger = logging.getLogger(__name__)

class ImageIndex:
    def __init__(self, index_path: str = "cab/image_index.faiss", 
                 metadata_path: str = "cab/image_metadata.pkl"):
        """
        初始化图像索引
        
        Args:
            index_path: FAISS索引文件路径
            metadata_path: 图像元数据文件路径
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []  # 存储 [(filename, answer), ...]
        self.feature_dim = 512  # OpenCLIP ViT-B-32的特征维度
        
        # 确保目录存在
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # 加载现有索引
        self.load_index()
    
    def load_index(self):
        """加载现有的FAISS索引和元数据"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                # 加载FAISS索引
                self.index = faiss.read_index(self.index_path)
                
                # 加载元数据
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"Loaded existing index with {len(self.metadata)} images")
            else:
                # 创建新索引
                self.index = faiss.IndexFlatIP(self.feature_dim)  # 内积索引(余弦相似度)
                self.metadata = []
                logger.info("Created new empty index")
                
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            # 创建新索引
            self.index = faiss.IndexFlatIP(self.feature_dim)
            self.metadata = []
    
    def save_index(self):
        """保存FAISS索引和元数据到文件"""
        try:
            # 保存FAISS索引
            faiss.write_index(self.index, self.index_path)
            
            # 保存元数据
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info(f"Saved index with {len(self.metadata)} images")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise
    
    def add_image(self, filename: str, answer: str, features: np.ndarray):
        """
        向索引中添加单张图像
        
        Args:
            filename: 图像文件名
            answer: 对应答案
            features: 特征向量
        """
        try:
            # 确保特征向量是2D数组
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # 添加到FAISS索引
            self.index.add(features.astype(np.float32))
            
            # 添加元数据
            self.metadata.append((filename, answer))
            
            logger.info(f"Added image to index: {filename}")
            
        except Exception as e:
            logger.error(f"Error adding image {filename} to index: {e}")
            raise
    
    def remove_image(self, filename: str):
        """
        从索引中移除图像（需要重建索引）
        
        Args:
            filename: 要移除的图像文件名
        """
        # 找到要移除的索引
        indices_to_remove = []
        for i, (fname, _) in enumerate(self.metadata):
            if fname == filename:
                indices_to_remove.append(i)
        
        if not indices_to_remove:
            logger.warning(f"Image {filename} not found in index")
            return
        
        # 移除元数据
        for i in reversed(indices_to_remove):
            del self.metadata[i]
        
        logger.info(f"Removed {len(indices_to_remove)} entries for {filename}")
        logger.info("Note: Index needs to be rebuilt for changes to take effect")
    
    def search_similar(self, query_features: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        搜索相似图像
        
        Args:
            query_features: 查询图像的特征向量
            top_k: 返回最相似的前k个结果
            
        Returns:
            相似图像列表，包含filename, answer, similarity
        """
        try:
            if self.index.ntotal == 0:
                logger.warning("Index is empty")
                return []
            
            # 确保特征向量是2D数组
            if query_features.ndim == 1:
                query_features = query_features.reshape(1, -1)
            
            # 搜索最相似的图像
            similarities, indices = self.index.search(
                query_features.astype(np.float32), 
                min(top_k, self.index.ntotal)
            )
            
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx >= 0 and idx < len(self.metadata):
                    filename, answer = self.metadata[idx]
                    results.append({
                        'filename': filename,
                        'answer': answer,
                        'similarity': float(similarity),
                        'rank': i + 1
                    })
            
            # 按相似度排序（降序）
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.info(f"Found {len(results)} similar images")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar images: {e}")
            return []
    
    def rebuild_index(self, questions_csv: str = "questions.csv", 
                     images_dir: str = "question-images"):
        """
        重建整个索引
        
        Args:
            questions_csv: 问题数据CSV文件路径
            images_dir: 图像目录路径
        """
        logger.info("Starting index rebuild...")
        
        try:
            # 加载问题数据
            if not os.path.exists(questions_csv):
                raise FileNotFoundError(f"Questions CSV file not found: {questions_csv}")
            
            df = pd.read_csv(questions_csv)
            if 'filename' not in df.columns or 'answer' not in df.columns:
                raise ValueError("CSV must contain 'filename' and 'answer' columns")
            
            # 初始化特征提取器
            extractor = ImageFeatureExtractor()
            
            # 创建新的空索引
            self.index = faiss.IndexFlatIP(self.feature_dim)
            self.metadata = []
            
            # 处理每张图像
            success_count = 0
            total_count = len(df)
            
            for _, row in df.iterrows():
                filename = row['filename']
                answer = row['answer']
                image_path = os.path.join(images_dir, filename)
                
                if not os.path.exists(image_path):
                    logger.warning(f"Image file not found: {image_path}")
                    continue
                
                # 提取特征
                features = extractor.extract_features(image_path)
                if features is not None:
                    self.add_image(filename, answer, features)
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        logger.info(f"Processed {success_count}/{total_count} images")
            
            # 保存索引
            self.save_index()
            
            logger.info(f"Index rebuild completed: {success_count}/{total_count} images processed")
            return success_count, total_count
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            'total_images': len(self.metadata),
            'index_size': self.index.ntotal if self.index else 0,
            'feature_dimension': self.feature_dim,
            'index_exists': os.path.exists(self.index_path),
            'metadata_exists': os.path.exists(self.metadata_path)
        }