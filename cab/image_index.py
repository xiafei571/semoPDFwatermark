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
import glob
import unicodedata

from .feature_extractor import ImageFeatureExtractor

logger = logging.getLogger(__name__)

# 新增: 规范化与路径解析工具
def _sanitize_filename(raw_name: str) -> str:
    """对CSV中的文件名进行鲁棒清洗，去除空白与常见标点，并标准化Unicode。"""
    name = str(raw_name)
    # Unicode 归一化（处理全角标点等）
    name = unicodedata.normalize('NFKC', name)
    # 去除首尾空白
    name = name.strip()
    # 去除首尾引号
    name = name.strip('"\'')
    # 去除末尾常见分隔标点（中英文逗号、句号、分号）与空白
    while len(name) > 0 and name[-1] in ['，', '。', '；', ',', ';', ' ']:
        name = name[:-1]
    # 仅保留文件名（去掉可能拼进来的路径）
    name = os.path.basename(name)
    return name

def _resolve_image_path(images_dir: str, filename: str) -> Optional[str]:
    """在区分大小写的文件系统上，尽可能匹配实际存在的文件路径。"""
    sanitized = _sanitize_filename(filename)
    direct_path = os.path.join(images_dir, sanitized)
    if os.path.exists(direct_path):
        return direct_path
    # 按不区分大小写尝试匹配完整文件名
    lower_target = sanitized.lower()
    try:
        for entry in os.listdir(images_dir):
            if entry.lower() == lower_target:
                return os.path.join(images_dir, entry)
    except FileNotFoundError:
        return None
    # 按同名不同扩展尝试
    stem, ext = os.path.splitext(sanitized)
    if stem:
        candidates = glob.glob(os.path.join(images_dir, stem) + ".*")
        if candidates:
            # 优先匹配相同扩展（忽略大小写）
            for c in candidates:
                if os.path.splitext(c)[1].lower() == ext.lower():
                    return c
            return candidates[0]
    return None

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
            
            # 搜索最相似的图像（第一阶段：向量召回）
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

            # 二阶段重排（可选）：使用 ORB 在左上ROI进行局部匹配，提升同图排序
            # 通过环境变量开启：CAB_ORB_RERANK=1，权重 CAB_ORB_WEIGHT (默认0.4)
            try:
                use_rerank = os.environ.get("CAB_ORB_RERANK", "1") not in {"0", "false", "False"}
                if use_rerank and results:
                    orb_weight = float(os.environ.get("CAB_ORB_WEIGHT", 0.4))
                    orb_weight = max(0.0, min(1.0, orb_weight))
                    # 懒加载提取器用于ORB
                    extractor = ImageFeatureExtractor()
                    # 查询图片路径不在此函数内，留在上层；因此此处仅做权重准备
                    # 我们在此不直接访问查询路径。改为让上层调用器在需要时传入。
            except Exception:
                pass
            
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
            
            # 校验并规范列
            if 'filename' not in df.columns:
                raise ValueError("CSV must contain 'filename' column")
            if 'answer' not in df.columns:
                df['answer'] = ""
            
            # 允许 answer 为空，统一为字符串
            df['answer'] = df['answer'].fillna("").astype(str)
            # 规范文件名，去空白与标点
            df['filename'] = df['filename'].astype(str).map(_sanitize_filename)
            # 丢弃无效文件名
            df = df[df['filename'] != ""]
            
            # 初始化特征提取器
            extractor = ImageFeatureExtractor()
            
            # 创建新的空索引
            self.index = faiss.IndexFlatIP(self.feature_dim)
            self.metadata = []
            
            # 处理每张图像
            success_count = 0
            total_count = len(df)
            missing_files = 0
            
            for _, row in df.iterrows():
                filename = row['filename']
                answer = row['answer']

                image_path = _resolve_image_path(images_dir, filename)
                if not image_path or not os.path.exists(image_path):
                    logger.warning(f"Image file not found: {os.path.join(images_dir, filename)}")
                    missing_files += 1
                    continue
                
                try:
                    # 提取特征
                    features = extractor.extract_features(image_path)
                    if features is not None:
                        self.add_image(os.path.basename(image_path), answer, features)
                        success_count += 1
                        
                        if success_count % 10 == 0:
                            logger.info(f"Processed {success_count}/{total_count} images")
                    else:
                        logger.warning(f"Feature extraction failed: {filename}")
                except Exception as ie:
                    logger.warning(f"Error processing {filename}: {ie}")
            
            # 保存索引
            self.save_index()
            
            logger.info(f"Index rebuild completed: {success_count}/{total_count} images processed (missing: {missing_files})")
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