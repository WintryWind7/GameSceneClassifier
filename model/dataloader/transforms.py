"""
GameSceneClassifier 数据预处理转换

提供游戏场景图像的预处理和数据变换功能
"""

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from typing import Union, Tuple, Optional, Callable, List
import random


class GameTransforms:
    """游戏场景的预处理转换类"""
    
    def __init__(self, 
                 target_size: Tuple[int, int] = (640, 640),
                 normalize: bool = True,
                 mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
                 std: Tuple[float, float, float] = (0.229, 0.224, 0.225)):
        """
        初始化转换器
        
        Args:
            target_size: 目标图像尺寸 (height, width)
            normalize: 是否进行标准化
            mean: 标准化均值
            std: 标准化标准差
        """
        self.target_size = target_size
        self.normalize = normalize
        self.mean = mean
        self.std = std
    
    # === 基础预处理方法 ===
    
    def resize_image(self, image: Union[np.ndarray, Image.Image], 
                    keep_aspect_ratio: bool = True) -> np.ndarray:
        """
        调整图像尺寸
        
        Args:
            image: 输入图像
            keep_aspect_ratio: 是否保持宽高比
            
        Returns:
            调整后的图像
        """
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        h, w = image.shape[:2]
        target_h, target_w = self.target_size
        
        if keep_aspect_ratio:
            # 保持宽高比的缩放
            scale = min(target_w / w, target_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # 缩放图像
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # 创建目标尺寸的画布并居中放置
            canvas = np.zeros((target_h, target_w, 3), dtype=image.dtype)
            y_offset = (target_h - new_h) // 2
            x_offset = (target_w - new_w) // 2
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            return canvas
        else:
            # 直接缩放到目标尺寸
            return cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    
    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像标准化
        
        Args:
            image: 输入图像 [0, 255]
            
        Returns:
            标准化后的图像
        """
        if not self.normalize:
            return image.astype(np.float32) / 255.0
        
        # 转换为 [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # 标准化
        for i in range(3):
            image[:, :, i] = (image[:, :, i] - self.mean[i]) / self.std[i]
        
        return image
    
    def extract_game_area(self, image: np.ndarray, 
                         ui_margin: int = 50) -> np.ndarray:
        """
        提取游戏主要区域，去除UI边框
        
        Args:
            image: 输入图像
            ui_margin: UI边距
            
        Returns:
            提取后的游戏区域
        """
        h, w = image.shape[:2]
        
        # 简单的边缘裁剪，去除可能的UI元素
        top = min(ui_margin, h // 10)
        bottom = max(h - ui_margin, h - h // 10)
        left = min(ui_margin, w // 10)
        right = max(w - ui_margin, w - w // 10)
        
        return image[top:bottom, left:right]
    
    def enhance_contrast(self, image: np.ndarray, alpha: float = 1.2) -> np.ndarray:
        """
        增强图像对比度
        
        Args:
            image: 输入图像
            alpha: 对比度增强系数
            
        Returns:
            增强后的图像
        """
        return np.clip(image * alpha, 0, 255).astype(image.dtype)
    
    def adjust_brightness(self, image: np.ndarray, beta: int = 10) -> np.ndarray:
        """
        调整图像亮度
        
        Args:
            image: 输入图像
            beta: 亮度调整值
            
        Returns:
            调整后的图像
        """
        return np.clip(image.astype(np.int16) + beta, 0, 255).astype(image.dtype)
    
    # === PyTorch变换管道 ===
    
    @staticmethod
    def get_train_transforms(target_size: Tuple[int, int] = (640, 640),
                           augment: bool = True) -> Callable:
        """
        获取训练时的变换管道
        
        Args:
            target_size: 目标尺寸
            augment: 是否进行数据增强
            
        Returns:
            变换函数
        """
        transforms_list = [
            T.Resize(target_size),
        ]
        
        if augment:
            transforms_list.extend([
                T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
                T.RandomHorizontalFlip(p=0.5),
                T.RandomRotation(degrees=5),
            ])
        
        transforms_list.extend([
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], 
                       std=[0.229, 0.224, 0.225])
        ])
        
        return T.Compose(transforms_list)
    
    @staticmethod
    def get_val_transforms(target_size: Tuple[int, int] = (640, 640)) -> Callable:
        """
        获取验证时的变换管道
        
        Args:
            target_size: 目标尺寸
            
        Returns:
            变换函数
        """
        return T.Compose([
            T.Resize(target_size),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], 
                       std=[0.229, 0.224, 0.225])
        ])
    
    @staticmethod
    def get_inference_transforms(target_size: Tuple[int, int] = (640, 640)) -> Callable:
        """
        获取推理时的变换管道
        
        Args:
            target_size: 目标尺寸
            
        Returns:
            变换函数
        """
        return GameTransforms.get_val_transforms(target_size)
    
    # === 完整的预处理流程 ===
    
    def preprocess_for_training(self, image: Union[np.ndarray, Image.Image]) -> torch.Tensor:
        """
        训练用的完整预处理流程
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的张量
        """
        # 转换为numpy数组
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # 提取游戏区域
        image = self.extract_game_area(image)
        
        # 调整尺寸
        image = self.resize_image(image)
        
        # 转换为PIL图像用于torchvision变换
        pil_image = Image.fromarray(image)
        
        # 应用训练变换
        transform = self.get_train_transforms(self.target_size)
        return transform(pil_image)
    
    def preprocess_for_inference(self, image: Union[np.ndarray, Image.Image]) -> torch.Tensor:
        """
        推理用的完整预处理流程
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的张量
        """
        # 转换为numpy数组
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # 提取游戏区域
        image = self.extract_game_area(image)
        
        # 调整尺寸
        image = self.resize_image(image)
        
        # 转换为PIL图像用于torchvision变换
        pil_image = Image.fromarray(image)
        
        # 应用推理变换
        transform = self.get_inference_transforms(self.target_size)
        return transform(pil_image)


class GameAugmentation:
    """游戏场景专用的数据增强（可选，暂时简化实现）"""
    
    @staticmethod
    def random_ui_overlay(image: np.ndarray, overlay_prob: float = 0.3) -> np.ndarray:
        """
        随机添加UI遮罩，模拟不同的游戏UI
        
        Args:
            image: 输入图像
            overlay_prob: 添加遮罩的概率
            
        Returns:
            增强后的图像
        """
        if random.random() > overlay_prob:
            return image
        
        h, w = image.shape[:2]
        
        # 随机在边缘添加黑色遮罩，模拟UI
        mask_size = random.randint(10, 50)
        
        # 随机选择边缘
        edge = random.choice(['top', 'bottom', 'left', 'right'])
        
        if edge == 'top':
            image[:mask_size, :] = 0
        elif edge == 'bottom':
            image[-mask_size:, :] = 0
        elif edge == 'left':
            image[:, :mask_size] = 0
        elif edge == 'right':
            image[:, -mask_size:] = 0
        
        return image
    
    @staticmethod
    def simulate_screen_effects(image: np.ndarray, effect_prob: float = 0.2) -> np.ndarray:
        """
        模拟屏幕效果（如扫描线、噪声等）
        
        Args:
            image: 输入图像
            effect_prob: 应用效果的概率
            
        Returns:
            增强后的图像
        """
        if random.random() > effect_prob:
            return image
        
        # 添加轻微的噪声
        noise = np.random.normal(0, 5, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return image


# === 便捷函数 ===

def create_game_transforms(mode: str = 'train', 
                          target_size: Tuple[int, int] = (640, 640),
                          **kwargs) -> Callable:
    """
    创建游戏场景变换函数的便捷方法
    
    Args:
        mode: 模式 ('train', 'val', 'inference')
        target_size: 目标尺寸
        **kwargs: 其他参数
        
    Returns:
        变换函数
    """
    if mode == 'train':
        return GameTransforms.get_train_transforms(target_size, **kwargs)
    elif mode in ['val', 'validation']:
        return GameTransforms.get_val_transforms(target_size)
    elif mode == 'inference':
        return GameTransforms.get_inference_transforms(target_size)
    else:
        raise ValueError(f"不支持的模式: {mode}")


def preprocess_game_image(image: Union[np.ndarray, Image.Image, str],
                         mode: str = 'inference',
                         target_size: Tuple[int, int] = (640, 640)) -> torch.Tensor:
    """
    预处理游戏图像的便捷函数
    
    Args:
        image: 输入图像（数组、PIL图像或文件路径）
        mode: 处理模式
        target_size: 目标尺寸
        
    Returns:
        预处理后的张量
    """
    # 如果是文件路径，先加载图像
    if isinstance(image, str):
        image = Image.open(image)
    
    # 创建变换器
    transforms = GameTransforms(target_size=target_size)
    
    # 根据模式选择预处理方法
    if mode == 'train':
        return transforms.preprocess_for_training(image)
    else:
        return transforms.preprocess_for_inference(image)

