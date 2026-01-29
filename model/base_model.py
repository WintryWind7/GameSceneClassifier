"""
GameSceneClassifier 基础模型类

定义所有游戏场景分类器的基础接口和通用方法
"""

import torch
import torch.nn as nn
from abc import ABC, abstractmethod
from typing import Union, Dict, Any, Optional
import numpy as np
from PIL import Image


class BaseGameClassifier(nn.Module, ABC):
    """游戏场景分类器的基础抽象类
    
    所有具体的分类器模型都应该继承此类，并实现抽象方法
    """
    
    def __init__(self, num_classes: int = 10, device: str = 'auto'):
        """
        初始化基础分类器
        
        Args:
            num_classes: 分类类别数量
            device: 计算设备 ('auto', 'cpu', 'cuda')
        """
        super(BaseGameClassifier, self).__init__()
        self.num_classes = num_classes
        self.device = self._setup_device(device)
        self.is_trained = False
        
    def _setup_device(self, device: str) -> torch.device:
        """设置计算设备"""
        if device == 'auto':
            return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return torch.device(device)
    
    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播 - 子类必须实现
        
        Args:
            x: 输入张量 [batch_size, channels, height, width]
            
        Returns:
            输出张量 [batch_size, num_classes]
        """
        pass
    
    def predict(self, image: Union[torch.Tensor, np.ndarray, Image.Image, str]) -> Dict[str, Any]:
        """
        预测单张图像的场景类别
        
        Args:
            image: 输入图像，支持多种格式
            
        Returns:
            预测结果字典，包含类别、置信度等信息
        """
        self.eval()
        with torch.no_grad():
            # 预处理图像
            input_tensor = self._preprocess_image(image)
            input_tensor = input_tensor.to(self.device)
            
            # 前向传播
            outputs = self.forward(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            
            # 获取预测结果
            confidence, predicted_class = torch.max(probabilities, 1)
            
            return {
                'predicted_class': predicted_class.item(),
                'confidence': confidence.item(),
                'probabilities': probabilities.cpu().numpy().tolist(),
                'raw_outputs': outputs.cpu().numpy().tolist()
            }
    
    def _preprocess_image(self, image: Union[torch.Tensor, np.ndarray, Image.Image, str]) -> torch.Tensor:
        """
        图像预处理
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的张量 [1, channels, height, width]
        """
        # 这里先返回一个占位符，具体实现在子类中
        # 或者通过transforms模块处理
        if isinstance(image, torch.Tensor):
            if image.dim() == 3:
                image = image.unsqueeze(0)  # 添加batch维度
            return image
        
        # 其他格式的图像处理将在transforms模块中实现
        # 这里先返回一个默认张量
        return torch.randn(1, 3, 640, 640)
    
    def load_weights(self, path: str, strict: bool = True) -> None:
        """
        加载模型权重
        
        Args:
            path: 权重文件路径
            strict: 是否严格匹配模型结构
        """
        try:
            checkpoint = torch.load(path, map_location=self.device)
            
            # 处理不同的保存格式
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                else:
                    state_dict = checkpoint
            else:
                state_dict = checkpoint
            
            self.load_state_dict(state_dict, strict=strict)
            self.is_trained = True
            print(f"成功加载权重: {path}")
            
        except Exception as e:
            print(f"加载权重失败: {e}")
            raise
    
    def save_weights(self, path: str, include_optimizer: bool = False, **kwargs) -> None:
        """
        保存模型权重
        
        Args:
            path: 保存路径
            include_optimizer: 是否包含优化器状态
            **kwargs: 其他要保存的信息
        """
        try:
            checkpoint = {
                'model_state_dict': self.state_dict(),
                'num_classes': self.num_classes,
                'is_trained': self.is_trained,
                **kwargs
            }
            
            torch.save(checkpoint, path)
            print(f"成功保存权重: {path}")
            
        except Exception as e:
            print(f"保存权重失败: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        return {
            'model_name': self.__class__.__name__,
            'num_classes': self.num_classes,
            'device': str(self.device),
            'is_trained': self.is_trained,
            'total_parameters': total_params,
            'trainable_parameters': trainable_params,
            'model_size_mb': total_params * 4 / (1024 * 1024)  # 假设float32
        }
    
    def to_device(self, device: Optional[str] = None) -> 'BaseGameClassifier':
        """
        移动模型到指定设备
        
        Args:
            device: 目标设备
            
        Returns:
            self
        """
        if device is not None:
            self.device = torch.device(device)
        
        return self.to(self.device)
    
    def set_eval_mode(self) -> None:
        """设置为评估模式"""
        self.eval()
        
    def set_train_mode(self) -> None:
        """设置为训练模式"""
        self.train()
    
    def __repr__(self) -> str:
        """模型字符串表示"""
        info = self.get_model_info()
        return (f"{info['model_name']}("
                f"num_classes={info['num_classes']}, "
                f"device={info['device']}, "
                f"parameters={info['total_parameters']:,})")
