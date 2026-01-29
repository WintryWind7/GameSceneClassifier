"""
GameSceneClassifier 数据集类

提供游戏场景分类的数据集实现
"""

import os
import json
import csv
from pathlib import Path
from typing import Union, List, Dict, Tuple, Optional, Callable, Any
import torch
from torch.utils.data import Dataset
import numpy as np
from PIL import Image
import cv2

from .transforms import GameTransforms, create_game_transforms


class GameSceneDataset(Dataset):
    """游戏场景数据集类"""
    
    def __init__(self,
                 data_dir: Union[str, Path],
                 labels_file: Optional[Union[str, Path]] = None,
                 transform: Optional[Callable] = None,
                 target_size: Tuple[int, int] = (640, 640),
                 mode: str = 'train',
                 class_names: Optional[List[str]] = None):
        """
        初始化游戏场景数据集
        
        Args:
            data_dir: 图像数据目录
            labels_file: 标签文件路径（JSON或CSV格式）
            transform: 图像变换函数
            target_size: 目标图像尺寸
            mode: 数据集模式 ('train', 'val', 'test')
            class_names: 类别名称列表
        """
        self.data_dir = Path(data_dir)
        self.labels_file = Path(labels_file) if labels_file else None
        self.target_size = target_size
        self.mode = mode
        self.class_names = class_names or []
        
        # 设置变换
        if transform is None:
            self.transform = create_game_transforms(mode, target_size)
        else:
            self.transform = transform
        
        # 加载数据
        self.samples = self._load_samples()
        self.num_classes = len(self.class_names) if self.class_names else self._get_num_classes()
        
        print(f"加载 {mode} 数据集: {len(self.samples)} 个样本, {self.num_classes} 个类别")
    
    def _load_samples(self) -> List[Dict[str, Any]]:
        """加载数据样本"""
        samples = []
        
        if self.labels_file and self.labels_file.exists():
            # 从标签文件加载
            samples = self._load_from_labels_file()
        else:
            # 从目录结构加载（假设每个子目录是一个类别）
            samples = self._load_from_directory_structure()
        
        return samples
    
    def _load_from_labels_file(self) -> List[Dict[str, Any]]:
        """从标签文件加载数据"""
        samples = []
        
        if self.labels_file.suffix.lower() == '.json':
            samples = self._load_from_json()
        elif self.labels_file.suffix.lower() == '.csv':
            samples = self._load_from_csv()
        else:
            raise ValueError(f"不支持的标签文件格式: {self.labels_file.suffix}")
        
        return samples
    
    def _load_from_json(self) -> List[Dict[str, Any]]:
        """从JSON文件加载数据"""
        with open(self.labels_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        samples = []
        
        # 处理不同的JSON格式
        if isinstance(data, dict):
            if 'samples' in data:
                # 格式: {"samples": [...], "class_names": [...]}
                samples_data = data['samples']
                if 'class_names' in data and not self.class_names:
                    self.class_names = data['class_names']
            elif 'images' in data:
                # 格式: {"images": [...]}
                samples_data = data['images']
            else:
                # 直接是样本字典
                samples_data = [data]
        else:
            # 直接是样本列表
            samples_data = data
        
        for item in samples_data:
            image_path = self.data_dir / item['image']
            if image_path.exists():
                samples.append({
                    'image_path': image_path,
                    'label': item['label'],
                    'class_name': item.get('class_name', str(item['label']))
                })
        
        return samples
    
    def _load_from_csv(self) -> List[Dict[str, Any]]:
        """从CSV文件加载数据"""
        samples = []
        
        with open(self.labels_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                image_path = self.data_dir / row['image']
                if image_path.exists():
                    samples.append({
                        'image_path': image_path,
                        'label': int(row['label']),
                        'class_name': row.get('class_name', str(row['label']))
                    })
        
        return samples
    
    def _load_from_directory_structure(self) -> List[Dict[str, Any]]:
        """从目录结构加载数据（每个子目录是一个类别）"""
        samples = []
        class_names = []
        
        # 获取所有子目录作为类别
        class_dirs = [d for d in self.data_dir.iterdir() if d.is_dir()]
        class_dirs.sort()  # 确保顺序一致
        
        for class_idx, class_dir in enumerate(class_dirs):
            class_name = class_dir.name
            class_names.append(class_name)
            
            # 获取该类别下的所有图像文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            for image_path in class_dir.iterdir():
                if image_path.suffix.lower() in image_extensions:
                    samples.append({
                        'image_path': image_path,
                        'label': class_idx,
                        'class_name': class_name
                    })
        
        if not self.class_names:
            self.class_names = class_names
        
        return samples
    
    def _get_num_classes(self) -> int:
        """获取类别数量"""
        if self.class_names:
            return len(self.class_names)
        
        labels = [sample['label'] for sample in self.samples]
        return len(set(labels))
    
    def __len__(self) -> int:
        """返回数据集大小"""
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        获取单个样本
        
        Args:
            idx: 样本索引
            
        Returns:
            (image_tensor, label) 元组
        """
        sample = self.samples[idx]
        
        # 加载图像
        image = self._load_image(sample['image_path'])
        
        # 应用变换
        if self.transform:
            image = self.transform(image)
        
        label = sample['label']
        
        return image, label
    
    def _load_image(self, image_path: Path) -> Image.Image:
        """
        加载图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            PIL图像对象
        """
        try:
            image = Image.open(image_path)
            
            # 确保是RGB格式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
        
        except Exception as e:
            print(f"加载图像失败 {image_path}: {e}")
            # 返回一个默认图像
            return Image.new('RGB', self.target_size, color=(128, 128, 128))
    
    def get_class_names(self) -> List[str]:
        """获取类别名称列表"""
        return self.class_names.copy()
    
    def get_sample_info(self, idx: int) -> Dict[str, Any]:
        """
        获取样本信息
        
        Args:
            idx: 样本索引
            
        Returns:
            样本信息字典
        """
        sample = self.samples[idx]
        return {
            'index': idx,
            'image_path': str(sample['image_path']),
            'label': sample['label'],
            'class_name': sample['class_name']
        }
    
    def get_class_distribution(self) -> Dict[str, int]:
        """获取类别分布统计"""
        distribution = {}
        for sample in self.samples:
            class_name = sample['class_name']
            distribution[class_name] = distribution.get(class_name, 0) + 1
        return distribution


class GameWindowDataset(Dataset):
    """实时游戏窗口数据集（用于在线学习或实时预测）"""
    
    def __init__(self,
                 window_name: str,
                 capture_interval: float = 1.0,
                 max_samples: int = 1000,
                 transform: Optional[Callable] = None,
                 target_size: Tuple[int, int] = (640, 640)):
        """
        初始化实时窗口数据集
        
        Args:
            window_name: 窗口名称
            capture_interval: 捕获间隔（秒）
            max_samples: 最大样本数
            transform: 图像变换
            target_size: 目标尺寸
        """
        self.window_name = window_name
        self.capture_interval = capture_interval
        self.max_samples = max_samples
        self.target_size = target_size
        
        if transform is None:
            self.transform = create_game_transforms('inference', target_size)
        else:
            self.transform = transform
        
        self.samples = []  # 存储捕获的图像
        self.labels = []   # 存储对应的标签（如果有）
    
    def capture_frame(self, label: Optional[int] = None) -> bool:
        """
        捕获当前窗口帧
        
        Args:
            label: 可选的标签
            
        Returns:
            是否成功捕获
        """
        try:
            # 这里需要实现窗口捕获逻辑
            # 暂时返回一个占位符
            # 实际实现会在utils模块中
            
            # 创建一个占位图像
            dummy_image = np.random.randint(0, 255, 
                                          (*self.target_size, 3), 
                                          dtype=np.uint8)
            
            # 添加到样本列表
            if len(self.samples) >= self.max_samples:
                # 移除最旧的样本
                self.samples.pop(0)
                if self.labels:
                    self.labels.pop(0)
            
            self.samples.append(dummy_image)
            if label is not None:
                self.labels.append(label)
            
            return True
            
        except Exception as e:
            print(f"捕获窗口失败: {e}")
            return False
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Union[torch.Tensor, Tuple[torch.Tensor, int]]:
        """获取样本"""
        image = self.samples[idx]
        
        # 转换为PIL图像
        pil_image = Image.fromarray(image)
        
        # 应用变换
        if self.transform:
            image_tensor = self.transform(pil_image)
        else:
            image_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        
        # 如果有标签，返回(image, label)，否则只返回image
        if idx < len(self.labels):
            return image_tensor, self.labels[idx]
        else:
            return image_tensor


class GameSceneSubset(Dataset):
    """游戏场景数据集的子集（用于数据集划分）"""
    
    def __init__(self, dataset: GameSceneDataset, indices: List[int]):
        """
        初始化数据集子集
        
        Args:
            dataset: 原始数据集
            indices: 子集索引列表
        """
        self.dataset = dataset
        self.indices = indices
    
    def __len__(self) -> int:
        return len(self.indices)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        return self.dataset[self.indices[idx]]
    
    def get_class_names(self) -> List[str]:
        return self.dataset.get_class_names()


# === 便捷函数 ===

def create_game_dataset(data_dir: Union[str, Path],
                       labels_file: Optional[Union[str, Path]] = None,
                       mode: str = 'train',
                       target_size: Tuple[int, int] = (640, 640),
                       **kwargs) -> GameSceneDataset:
    """
    创建游戏场景数据集的便捷函数
    
    Args:
        data_dir: 数据目录
        labels_file: 标签文件
        mode: 模式
        target_size: 目标尺寸
        **kwargs: 其他参数
        
    Returns:
        数据集对象
    """
    return GameSceneDataset(
        data_dir=data_dir,
        labels_file=labels_file,
        mode=mode,
        target_size=target_size,
        **kwargs
    )


def split_dataset(dataset: GameSceneDataset, 
                 train_ratio: float = 0.8,
                 val_ratio: float = 0.1,
                 test_ratio: float = 0.1,
                 random_seed: int = 42) -> Tuple[GameSceneSubset, GameSceneSubset, GameSceneSubset]:
    """
    划分数据集为训练/验证/测试集
    
    Args:
        dataset: 原始数据集
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        random_seed: 随机种子
        
    Returns:
        (train_dataset, val_dataset, test_dataset) 元组
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "比例之和必须等于1"
    
    # 设置随机种子
    np.random.seed(random_seed)
    
    # 获取所有索引并打乱
    indices = list(range(len(dataset)))
    np.random.shuffle(indices)
    
    # 计算划分点
    n_samples = len(dataset)
    n_train = int(n_samples * train_ratio)
    n_val = int(n_samples * val_ratio)
    
    # 划分索引
    train_indices = indices[:n_train]
    val_indices = indices[n_train:n_train + n_val]
    test_indices = indices[n_train + n_val:]
    
    # 创建子集
    train_dataset = GameSceneSubset(dataset, train_indices)
    val_dataset = GameSceneSubset(dataset, val_indices)
    test_dataset = GameSceneSubset(dataset, test_indices)
    
    return train_dataset, val_dataset, test_dataset

