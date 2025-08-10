"""
图像特征提取模块
使用OpenCLIP模型提取图像特征向量
"""

import os
import numpy as np
import torch
from PIL import Image
import open_clip
import cv2
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImageFeatureExtractor:
    def __init__(self, model_name: str = None, pretrained: str = None, checkpoint_path: Optional[str] = None):
        """
        初始化图像特征提取器
        
        Args:
            model_name: OpenCLIP模型名称（默认从环境变量 CAB_MODEL_NAME 或 "ViT-B-32"）
            pretrained: 预训练权重版本（默认从环境变量 CAB_PRETRAINED 或 "openai"）
            checkpoint_path: 本地自定义权重路径（默认从环境变量 CAB_CHECKPOINT_PATH 或 "cab/model.pt"）
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # 环境变量优先
        model_name = model_name or os.environ.get("CAB_MODEL_NAME", "ViT-B-32")
        pretrained = pretrained or os.environ.get("CAB_PRETRAINED", "openai")
        checkpoint_path = checkpoint_path or os.environ.get("CAB_CHECKPOINT_PATH", "cab/model.pt")
        
        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name, pretrained=pretrained, device=self.device
            )
            self.model.eval()
            logger.info(f"Loaded OpenCLIP model: {model_name} ({pretrained})")
            
            # 可选加载本地自定义权重
            if checkpoint_path and os.path.exists(checkpoint_path):
                try:
                    ckpt = torch.load(checkpoint_path, map_location=self.device)
                    state = ckpt.get("state_dict", ckpt)
                    missing, unexpected = self.model.load_state_dict(state, strict=False)
                    logger.info(f"Loaded custom checkpoint: {checkpoint_path} (missing={len(missing)}, unexpected={len(unexpected)})")
                except Exception as ce:
                    logger.warning(f"Failed to load custom checkpoint {checkpoint_path}: {ce}")
        except Exception as e:
            logger.error(f"Failed to load OpenCLIP model: {e}")
            raise
    
    def preprocess_image(self, image_path: str) -> Optional[torch.Tensor]:
        """
        预处理图像，支持各种变形处理
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            预处理后的图像张量
        """
        try:
            # 读取图像
            if isinstance(image_path, str):
                image = Image.open(image_path).convert('RGB')
            else:
                # 如果传入的是PIL Image对象
                image = image_path.convert('RGB')
            
            # 应用预处理
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            return image_tensor
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None
    
    def extract_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        提取单张图像的特征向量
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            归一化的特征向量 (numpy数组)
        """
        image_tensor = self.preprocess_image(image_path)
        if image_tensor is None:
            return None
            
        try:
            with torch.no_grad():
                # 提取图像特征
                features = self.model.encode_image(image_tensor)
                # L2归一化
                features = features / features.norm(dim=-1, keepdim=True)
                # 转换为numpy数组
                features = features.cpu().numpy().flatten()
                
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from {image_path}: {e}")
            return None
    
    def extract_batch_features(self, image_paths: List[str]) -> Tuple[List[np.ndarray], List[str]]:
        """
        批量提取图像特征
        
        Args:
            image_paths: 图像文件路径列表
            
        Returns:
            (特征向量列表, 成功处理的文件名列表)
        """
        features_list = []
        valid_paths = []
        
        for image_path in image_paths:
            features = self.extract_features(image_path)
            if features is not None:
                features_list.append(features)
                valid_paths.append(os.path.basename(image_path))
                logger.info(f"Extracted features for: {image_path}")
            else:
                logger.warning(f"Failed to extract features for: {image_path}")
        
        logger.info(f"Successfully extracted features for {len(features_list)}/{len(image_paths)} images")
        return features_list, valid_paths
    
    def augment_image(self, image: Image.Image) -> List[Image.Image]:
        """
        对图像进行数据增强，支持旋转、缩放等变形
        
        Args:
            image: PIL Image对象
            
        Returns:
            增强后的图像列表
        """
        augmented = [image]  # 原始图像
        
        # 旋转增强 (±5度、±10度)
        for angle in [-10, -5, 5, 10]:
            rotated = image.rotate(angle, expand=False, fillcolor='white')
            augmented.append(rotated)
        
        # 缩放增强
        w, h = image.size
        for scale in [0.9, 1.1]:
            new_w, new_h = int(w * scale), int(h * scale)
            scaled = image.resize((new_w, new_h), Image.LANCZOS)
            # 如果缩放后大于原尺寸，进行中心裁剪
            if scale > 1.0:
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                scaled = scaled.crop((left, top, left + w, top + h))
            # 如果缩放后小于原尺寸，进行填充
            elif scale < 1.0:
                new_img = Image.new('RGB', (w, h), 'white')
                paste_x = (w - new_w) // 2
                paste_y = (h - new_h) // 2
                new_img.paste(scaled, (paste_x, paste_y))
                scaled = new_img
            augmented.append(scaled)
        
        return augmented