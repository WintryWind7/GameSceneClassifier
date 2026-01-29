"""
GameSceneClassifier 数据加载器

提供高效的数据加载和批处理功能
"""

from typing import Optional, Dict, Any, Tuple, Union
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
import numpy as np
from collections import Counter

from .datasets import GameSceneDataset, GameSceneSubset, split_dataset


class GameDataLoader:
    """游戏场景数据加载器管理类"""
    
    def __init__(self,
                 dataset: Union[GameSceneDataset, GameSceneSubset],
                 batch_size: int = 32,
                 shuffle: bool = True,
                 num_workers: int = 4,
                 pin_memory: bool = True,
                 drop_last: bool = False,
                 use_weighted_sampling: bool = False):
        """
        初始化数据加载器
        
        Args:
            dataset: 数据集对象
            batch_size: 批次大小
            shuffle: 是否打乱数据
            num_workers: 工作进程数
            pin_memory: 是否固定内存
            drop_last: 是否丢弃最后不完整的批次
            use_weighted_sampling: 是否使用加权采样（处理类别不平衡）
        """
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.num_workers = num_workers
        self.pin_memory = pin_memory
        self.drop_last = drop_last
        self.use_weighted_sampling = use_weighted_sampling
        
        # 创建采样器
        self.sampler = self._create_sampler() if use_weighted_sampling else None
        
        # 创建数据加载器
        self.dataloader = self._create_dataloader()
    
    def _create_sampler(self) -> Optional[WeightedRandomSampler]:
        """创建加权采样器以处理类别不平衡"""
        if not self.use_weighted_sampling:
            return None
        
        # 统计各类别样本数量
        labels = []
        for i in range(len(self.dataset)):
            _, label = self.dataset[i]
            labels.append(label)
        
        # 计算类别权重
        label_counts = Counter(labels)
        total_samples = len(labels)
        num_classes = len(label_counts)
        
        # 计算每个样本的权重
        weights = []
        for label in labels:
            class_count = label_counts[label]
            weight = total_samples / (num_classes * class_count)
            weights.append(weight)
        
        return WeightedRandomSampler(
            weights=weights,
            num_samples=len(weights),
            replacement=True
        )
    
    def _create_dataloader(self) -> DataLoader:
        """创建PyTorch数据加载器"""
        # 如果使用采样器，则不能同时shuffle
        shuffle = self.shuffle if self.sampler is None else False
        
        return DataLoader(
            dataset=self.dataset,
            batch_size=self.batch_size,
            shuffle=shuffle,
            sampler=self.sampler,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            drop_last=self.drop_last,
            collate_fn=self._collate_fn
        )
    
    def _collate_fn(self, batch):
        """自定义批处理函数"""
        # 默认的collate函数已经足够好了
        # 如果需要特殊处理，可以在这里实现
        return torch.utils.data.dataloader.default_collate(batch)
    
    def __iter__(self):
        """迭代器接口"""
        return iter(self.dataloader)
    
    def __len__(self):
        """返回批次数量"""
        return len(self.dataloader)
    
    def get_batch_info(self) -> Dict[str, Any]:
        """获取批次信息"""
        return {
            'batch_size': self.batch_size,
            'num_batches': len(self.dataloader),
            'total_samples': len(self.dataset),
            'num_workers': self.num_workers,
            'use_weighted_sampling': self.use_weighted_sampling
        }


class GameDataManager:
    """游戏数据管理器，统一管理训练/验证/测试数据加载器"""
    
    def __init__(self,
                 dataset: GameSceneDataset,
                 batch_size: int = 32,
                 num_workers: int = 4,
                 train_ratio: float = 0.8,
                 val_ratio: float = 0.1,
                 test_ratio: float = 0.1,
                 use_weighted_sampling: bool = False,
                 random_seed: int = 42):
        """
        初始化数据管理器
        
        Args:
            dataset: 完整数据集
            batch_size: 批次大小
            num_workers: 工作进程数
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            test_ratio: 测试集比例
            use_weighted_sampling: 是否使用加权采样
            random_seed: 随机种子
        """
        self.dataset = dataset
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.use_weighted_sampling = use_weighted_sampling
        
        # 划分数据集
        self.train_dataset, self.val_dataset, self.test_dataset = split_dataset(
            dataset, train_ratio, val_ratio, test_ratio, random_seed
        )
        
        # 创建数据加载器
        self.train_loader = self._create_train_loader()
        self.val_loader = self._create_val_loader()
        self.test_loader = self._create_test_loader()
        
        print(f"数据集划分完成:")
        print(f"  训练集: {len(self.train_dataset)} 样本")
        print(f"  验证集: {len(self.val_dataset)} 样本")
        print(f"  测试集: {len(self.test_dataset)} 样本")
    
    def _create_train_loader(self) -> GameDataLoader:
        """创建训练数据加载器"""
        return GameDataLoader(
            dataset=self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=True,
            drop_last=True,
            use_weighted_sampling=self.use_weighted_sampling
        )
    
    def _create_val_loader(self) -> GameDataLoader:
        """创建验证数据加载器"""
        return GameDataLoader(
            dataset=self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
            drop_last=False,
            use_weighted_sampling=False
        )
    
    def _create_test_loader(self) -> GameDataLoader:
        """创建测试数据加载器"""
        return GameDataLoader(
            dataset=self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
            drop_last=False,
            use_weighted_sampling=False
        )
    
    def get_train_loader(self) -> GameDataLoader:
        """获取训练数据加载器"""
        return self.train_loader
    
    def get_val_loader(self) -> GameDataLoader:
        """获取验证数据加载器"""
        return self.val_loader
    
    def get_test_loader(self) -> GameDataLoader:
        """获取测试数据加载器"""
        return self.test_loader
    
    def get_class_names(self) -> list:
        """获取类别名称"""
        return self.dataset.get_class_names()
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """获取数据集信息"""
        return {
            'total_samples': len(self.dataset),
            'num_classes': self.dataset.num_classes,
            'class_names': self.get_class_names(),
            'train_samples': len(self.train_dataset),
            'val_samples': len(self.val_dataset),
            'test_samples': len(self.test_dataset),
            'batch_size': self.batch_size,
            'class_distribution': self.dataset.get_class_distribution()
        }
    
    def get_sample_batch(self, loader_type: str = 'train') -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取一个样本批次（用于调试和可视化）
        
        Args:
            loader_type: 加载器类型 ('train', 'val', 'test')
            
        Returns:
            (images, labels) 批次
        """
        if loader_type == 'train':
            loader = self.train_loader
        elif loader_type == 'val':
            loader = self.val_loader
        elif loader_type == 'test':
            loader = self.test_loader
        else:
            raise ValueError(f"不支持的加载器类型: {loader_type}")
        
        # 获取第一个批次
        for batch in loader:
            return batch
        
        # 如果没有数据，返回空批次
        return torch.empty(0), torch.empty(0)


# === 便捷函数 ===

def create_game_dataloader(dataset: Union[GameSceneDataset, GameSceneSubset],
                          batch_size: int = 32,
                          mode: str = 'train',
                          **kwargs) -> GameDataLoader:
    """
    创建游戏数据加载器的便捷函数
    
    Args:
        dataset: 数据集
        batch_size: 批次大小
        mode: 模式 ('train', 'val', 'test')
        **kwargs: 其他参数
        
    Returns:
        数据加载器
    """
    # 根据模式设置默认参数
    if mode == 'train':
        default_kwargs = {
            'shuffle': True,
            'drop_last': True,
            'use_weighted_sampling': kwargs.get('use_weighted_sampling', False)
        }
    else:
        default_kwargs = {
            'shuffle': False,
            'drop_last': False,
            'use_weighted_sampling': False
        }
    
    # 合并参数
    final_kwargs = {**default_kwargs, **kwargs}
    
    return GameDataLoader(
        dataset=dataset,
        batch_size=batch_size,
        **final_kwargs
    )


def create_data_manager(data_dir: str,
                       labels_file: Optional[str] = None,
                       batch_size: int = 32,
                       target_size: Tuple[int, int] = (640, 640),
                       **kwargs) -> GameDataManager:
    """
    创建数据管理器的便捷函数
    
    Args:
        data_dir: 数据目录
        labels_file: 标签文件
        batch_size: 批次大小
        target_size: 目标尺寸
        **kwargs: 其他参数
        
    Returns:
        数据管理器
    """
    # 创建数据集
    dataset = GameSceneDataset(
        data_dir=data_dir,
        labels_file=labels_file,
        target_size=target_size,
        mode='train'  # 这里用train模式，后续会自动划分
    )
    
    # 创建数据管理器
    return GameDataManager(
        dataset=dataset,
        batch_size=batch_size,
        **kwargs
    )


def get_dataloader_stats(dataloader: GameDataLoader) -> Dict[str, Any]:
    """
    获取数据加载器统计信息
    
    Args:
        dataloader: 数据加载器
        
    Returns:
        统计信息字典
    """
    # 统计一个epoch的信息
    total_samples = 0
    label_counts = Counter()
    
    for batch_images, batch_labels in dataloader:
        total_samples += len(batch_labels)
        for label in batch_labels.tolist():
            label_counts[label] += 1
    
    return {
        'total_samples': total_samples,
        'num_batches': len(dataloader),
        'batch_size': dataloader.batch_size,
        'label_distribution': dict(label_counts),
        'samples_per_class': {
            f'class_{k}': v for k, v in label_counts.items()
        }
    }

