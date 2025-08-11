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

# 新增：解析区域配置与裁剪辅助

def _parse_focus_region(env_value: Optional[str]) -> Tuple[str, float]:
    """
    解析环境变量 CAB_FOCUS_REGION，例如："top_left:0.6"。
    返回 (区域名, 比例)，区域名支持：top_left, center。
    默认返回 ("top_left", 0.6)。
    """
    try:
        if not env_value:
            return "top_left", 0.6
        parts = str(env_value).split(":")
        region = parts[0].strip() if parts[0].strip() else "top_left"
        ratio = float(parts[1]) if len(parts) > 1 else 0.6
        ratio = max(0.2, min(0.95, ratio))  # 限制在合理范围
        if region not in {"top_left", "center"}:
            region = "top_left"
        return region, ratio
    except Exception:
        return "top_left", 0.6


def _crop_region(image: Image.Image, region: str, ratio: float) -> Image.Image:
    """
    根据区域与比例裁剪图像。
    - top_left: 取左上角 (ratio*W, ratio*H)
    - center:   取中心区域，边长为 ratio
    """
    w, h = image.size
    cw, ch = int(w * ratio), int(h * ratio)
    if region == "center":
        left = (w - cw) // 2
        top = (h - ch) // 2
    else:  # top_left
        left = 0
        top = 0
    right = min(w, left + cw)
    bottom = min(h, top + ch)
    return image.crop((left, top, right, bottom))

# 新增：OpenCV辅助

def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    arr = np.array(image.convert('RGB'))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _detect_symbol_roi_top_left(image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """
    基于阈值与轮廓的左上角主要符号区域检测。
    - 先在左上搜索窗口（比率 CAB_ROI_SEARCH_RATIO，默认0.7）内寻找最大的非白色连通域。
    - 通过形态学去噪并取最大外接矩形，返回 (left, top, right, bottom)。
    失败返回 None。
    """
    try:
        search_ratio = float(os.environ.get("CAB_ROI_SEARCH_RATIO", 0.7))
        search_ratio = max(0.4, min(0.95, search_ratio))
        min_area_frac = float(os.environ.get("CAB_ROI_MIN_AREA_FRAC", 0.001))  # 相对全图面积
        pad = int(os.environ.get("CAB_ROI_PAD", 8))

        bgr = _pil_to_bgr(image)
        H, W = bgr.shape[:2]
        sw, sh = int(W * search_ratio), int(H * search_ratio)
        roi = bgr[0:sh, 0:sw]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # 先试固定高阈值（白底上黑线），失败再用Otsu
        _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
        if mask.sum() < 500:  # 像素过少，改用 Otsu
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # 形态学去噪 + 连通
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # 选择面积最大的候选，且面积需超过阈值
        full_area = H * W
        best_rect = None
        best_area = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            # 基本过滤：不能太小
            if area < max(50, int(full_area * min_area_frac)):
                continue
            # 偏好更靠近左上角的候选（通过左上坐标加权）
            score = area - 0.1 * (x + y)
            if score > best_area:
                best_area = score
                best_rect = (x, y, w, h)

        if best_rect is None:
            return None

        x, y, w, h = best_rect
        # 映射回全图坐标系，并加边距
        left = max(0, x - pad)
        top = max(0, y - pad)
        right = min(W, x + w + pad)
        bottom = min(H, y + h + pad)
        # 转换为全图坐标
        return (left, top, right, bottom)
    except Exception as e:
        logger.warning(f"ROI detection failed: {e}")
        return None


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
        提取单张图像的特征向量（优先检测左上主要符号ROI，再与全图加权融合）
        """
        # 读取原始图，保留 PIL 以便裁剪
        try:
            image = Image.open(image_path).convert('RGB') if isinstance(image_path, str) else image_path.convert('RGB')
        except Exception as e:
            logger.error(f"Error opening image {image_path}: {e}")
            return None

        # 配置
        region_spec = os.environ.get("CAB_FOCUS_REGION", "top_left:0.6")
        region, ratio = _parse_focus_region(region_spec)
        alpha = float(os.environ.get("CAB_REGION_WEIGHT", 0.7))
        alpha = max(0.0, min(1.0, alpha))
        use_roi = os.environ.get("CAB_ROI_DETECT", "1") not in {"0", "false", "False"}

        # 先计算全图特征
        try:
            image_tensor_full = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                feat_full = self.model.encode_image(image_tensor_full)
                feat_full = feat_full / feat_full.norm(dim=-1, keepdim=True)
                feat_full = feat_full.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Error encoding full image {image_path}: {e}")
            return None

        feat_roi = None
        if use_roi:
            # 自动检测左上符号ROI
            box = _detect_symbol_roi_top_left(image)
            if box is not None:
                l, t, r, b = box
                try:
                    roi_img = image.crop((l, t, r, b))
                    image_tensor_roi = self.preprocess(roi_img).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        feat_roi = self.model.encode_image(image_tensor_roi)
                        feat_roi = feat_roi / feat_roi.norm(dim=-1, keepdim=True)
                        feat_roi = feat_roi.cpu().numpy().flatten()
                except Exception as e:
                    logger.warning(f"Encoding ROI failed, fallback to heuristic crop: {e}")
                    feat_roi = None

        if feat_roi is None:
            # 回退到启发式左上裁剪
            try:
                cropped = _crop_region(image, region, ratio)
                image_tensor_crop = self.preprocess(cropped).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    feat_roi = self.model.encode_image(image_tensor_crop)
                    feat_roi = feat_roi / feat_roi.norm(dim=-1, keepdim=True)
                    feat_roi = feat_roi.cpu().numpy().flatten()
            except Exception as e:
                logger.warning(f"Heuristic crop failed for {image_path}: {e}")
                feat_roi = None

        # 融合并归一化
        if feat_roi is not None:
            combined = alpha * feat_roi + (1.0 - alpha) * feat_full
            norm = np.linalg.norm(combined) + 1e-12
            combined = combined / norm
            return combined.astype(np.float32)
        else:
            return feat_full.astype(np.float32)
    
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

    # ============== 新增：ORB 局部匹配相似度（用于二阶段重排） ==============
    def compute_orb_similarity(self, query_image_path: str, candidate_image_path: str) -> float:
        """
        在左上角 ROI 范围内使用 ORB 做局部匹配，返回 [0,1] 的相似度。
        - 先尝试自动ROI检测，失败则用启发式裁剪(top_left:ratio)
        - 采用 Lowe 比例测试过滤匹配
        - 按好匹配数占最小关键点数的比例归一化
        """
        try:
            # 读取两张图
            qa = Image.open(query_image_path).convert('RGB') if isinstance(query_image_path, str) else query_image_path.convert('RGB')
            ca = Image.open(candidate_image_path).convert('RGB') if isinstance(candidate_image_path, str) else candidate_image_path.convert('RGB')

            # ROI 获取
            def get_roi(img: Image.Image) -> np.ndarray:
                box = _detect_symbol_roi_top_left(img)
                if box is None:
                    region, ratio = _parse_focus_region(os.environ.get("CAB_FOCUS_REGION", "top_left:0.6"))
                    img = _crop_region(img, region, ratio)
                else:
                    l, t, r, b = box
                    img = img.crop((l, t, r, b))
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

            g1 = get_roi(qa)
            g2 = get_roi(ca)

            # ORB 提取
            orb = cv2.ORB_create(nfeatures=int(os.environ.get("CAB_ORB_NFEATURES", 500)))
            k1, d1 = orb.detectAndCompute(g1, None)
            k2, d2 = orb.detectAndCompute(g2, None)
            if d1 is None or d2 is None or len(k1) < 10 or len(k2) < 10:
                return 0.0

            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            knn = matcher.knnMatch(d1, d2, k=2)
            ratio = float(os.environ.get("CAB_ORB_RATIO", 0.75))
            good = []
            for m, n in knn:
                if m.distance < ratio * n.distance:
                    good.append(m)
            if not good:
                return 0.0
            denom = max(1, min(len(k1), len(k2)))
            score = min(1.0, len(good) / denom)
            return float(score)
        except Exception as e:
            logger.warning(f"ORB similarity failed: {e}")
            return 0.0