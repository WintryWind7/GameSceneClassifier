"""
GameSceneClassifier 场景分类网络架构

专用于游戏场景分类的CNN网络实现
包含多种经典和现代的分类网络架构
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional, List, Tuple
import math

from ..base_model import BaseGameClassifier


class ConvBlock(nn.Module):
    """基础卷积块"""
    
    def __init__(self, in_channels: int, out_channels: int, 
                 kernel_size: int = 3, stride: int = 1, 
                 padding: Optional[int] = None, groups: int = 1,
                 activation: bool = True, dropout: float = 0.0):
        super(ConvBlock, self).__init__()
        
        if padding is None:
            padding = kernel_size // 2
        
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size, 
            stride, padding, groups=groups, bias=False
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.activation = nn.ReLU(inplace=True) if activation else nn.Identity()
        self.dropout = nn.Dropout2d(dropout) if dropout > 0 else nn.Identity()
    
    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.activation(x)
        x = self.dropout(x)
        return x


class ResidualBlock(nn.Module):
    """残差块 - 用于深层网络"""
    
    def __init__(self, in_channels: int, out_channels: int, 
                 stride: int = 1, downsample: Optional[nn.Module] = None):
        super(ResidualBlock, self).__init__()
        
        self.conv1 = ConvBlock(in_channels, out_channels, 3, stride)
        self.conv2 = ConvBlock(out_channels, out_channels, 3, 1, activation=False)
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        identity = x
        
        out = self.conv1(x)
        out = self.conv2(out)
        
        if self.downsample is not None:
            identity = self.downsample(x)
        
        out += identity
        out = self.relu(out)
        
        return out


class AttentionModule(nn.Module):
    """注意力模块 - 增强重要特征"""
    
    def __init__(self, channels: int, reduction: int = 16):
        super(AttentionModule, self).__init__()
        
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        b, c, _, _ = x.size()
        
        # 全局平均池化
        y = self.global_pool(x).view(b, c)
        
        # 通道注意力
        y = self.fc(y).view(b, c, 1, 1)
        
        # 应用注意力权重
        return x * y.expand_as(x)


class GameSceneNet(BaseGameClassifier):
    """游戏场景分类网络 - 轻量级高效架构"""
    
    def __init__(self, 
                 num_classes: int = 10,
                 input_size: int = 224,
                 dropout: float = 0.2,
                 use_attention: bool = True,
                 device: str = 'auto'):
        """
        初始化游戏场景分类网络
        
        Args:
            num_classes: 分类类别数
            input_size: 输入图像尺寸
            dropout: Dropout比例
            use_attention: 是否使用注意力机制
            device: 计算设备
        """
        super(GameSceneNet, self).__init__(num_classes, device)
        
        self.input_size = input_size
        self.use_attention = use_attention
        
        # 特征提取层
        self.features = nn.Sequential(
            # 第一阶段: 64x64
            ConvBlock(3, 32, 7, 2, 3),  # 224->112
            nn.MaxPool2d(3, 2, 1),      # 112->56
            
            # 第二阶段: 32x32  
            ConvBlock(32, 64, 3, 1),
            ConvBlock(64, 64, 3, 2),    # 56->28
            
            # 第三阶段: 16x16
            ConvBlock(64, 128, 3, 1),
            ConvBlock(128, 128, 3, 2),  # 28->14
            
            # 第四阶段: 8x8
            ConvBlock(128, 256, 3, 1),
            ConvBlock(256, 256, 3, 2),  # 14->7
            
            # 第五阶段: 4x4
            ConvBlock(256, 512, 3, 1),
            ConvBlock(512, 512, 3, 2),  # 7->3 (实际会是3x3或4x4)
        )
        
        # 注意力模块
        if use_attention:
            self.attention = AttentionModule(512)
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )
        
        # 初始化权重
        self._initialize_weights()
        
        # 移动到设备
        self.to_device()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量 [batch_size, 3, height, width]
            
        Returns:
            分类logits [batch_size, num_classes]
        """
        # 特征提取
        x = self.features(x)
        
        # 注意力机制
        if self.use_attention:
            x = self.attention(x)
        
        # 分类
        x = self.classifier(x)
        
        return x
    
    def _initialize_weights(self):
        """初始化网络权重"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = super().get_model_info()
        base_info.update({
            'model_type': 'GameSceneNet',
            'input_size': self.input_size,
            'use_attention': self.use_attention,
            'architecture': 'Custom CNN for Game Scene Classification'
        })
        return base_info


class ResNetSceneClassifier(BaseGameClassifier):
    """基于ResNet的游戏场景分类器"""
    
    def __init__(self, 
                 num_classes: int = 10,
                 layers: List[int] = [2, 2, 2, 2],  # ResNet18配置
                 dropout: float = 0.2,
                 device: str = 'auto'):
        """
        初始化ResNet场景分类器
        
        Args:
            num_classes: 分类类别数
            layers: 每个阶段的层数
            dropout: Dropout比例
            device: 计算设备
        """
        super(ResNetSceneClassifier, self).__init__(num_classes, device)
        
        self.layers = layers
        
        # 初始卷积层
        self.conv1 = ConvBlock(3, 64, 7, 2, 3)
        self.maxpool = nn.MaxPool2d(3, 2, 1)
        
        # ResNet阶段
        self.layer1 = self._make_layer(64, 64, layers[0], 1)
        self.layer2 = self._make_layer(64, 128, layers[1], 2)
        self.layer3 = self._make_layer(128, 256, layers[2], 2)
        self.layer4 = self._make_layer(256, 512, layers[3], 2)
        
        # 分类器
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(512, num_classes)
        
        # 初始化权重
        self._initialize_weights()
        
        # 移动到设备
        self.to_device()
    
    def _make_layer(self, in_channels: int, out_channels: int, 
                   blocks: int, stride: int) -> nn.Sequential:
        """构建ResNet层"""
        downsample = None
        if stride != 1 or in_channels != out_channels:
            downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        
        layers = []
        layers.append(ResidualBlock(in_channels, out_channels, stride, downsample))
        
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels))
        
        return nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        x = self.conv1(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        x = self.fc(x)
        
        return x
    
    def _initialize_weights(self):
        """初始化权重"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = super().get_model_info()
        base_info.update({
            'model_type': 'ResNetSceneClassifier',
            'layers_config': self.layers,
            'architecture': 'ResNet for Game Scene Classification'
        })
        return base_info


class EfficientSceneNet(BaseGameClassifier):
    """轻量级高效场景分类网络"""
    
    def __init__(self, 
                 num_classes: int = 10,
                 width_multiplier: float = 1.0,
                 dropout: float = 0.2,
                 device: str = 'auto'):
        """
        初始化高效场景网络
        
        Args:
            num_classes: 分类类别数
            width_multiplier: 宽度倍数（控制网络大小）
            dropout: Dropout比例
            device: 计算设备
        """
        super(EfficientSceneNet, self).__init__(num_classes, device)
        
        self.width_multiplier = width_multiplier
        
        # 计算通道数
        def make_divisible(v, divisor=8):
            new_v = max(divisor, int(v + divisor / 2) // divisor * divisor)
            if new_v < 0.9 * v:
                new_v += divisor
            return new_v
        
        # 网络配置 [输出通道, 重复次数, 步长]
        configs = [
            [make_divisible(32 * width_multiplier), 1, 2],
            [make_divisible(64 * width_multiplier), 2, 2], 
            [make_divisible(128 * width_multiplier), 3, 2],
            [make_divisible(256 * width_multiplier), 4, 2],
            [make_divisible(512 * width_multiplier), 2, 2],
        ]
        
        # 构建网络
        layers = []
        input_channels = 3
        
        # 初始层
        first_channels = make_divisible(32 * width_multiplier)
        layers.append(ConvBlock(input_channels, first_channels, 3, 2))
        input_channels = first_channels
        
        # 主要层
        for out_channels, repeats, stride in configs:
            for i in range(repeats):
                s = stride if i == 0 else 1
                layers.append(ConvBlock(input_channels, out_channels, 3, s))
                input_channels = out_channels
        
        self.features = nn.Sequential(*layers)
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(input_channels, num_classes)
        )
        
        # 初始化权重
        self._initialize_weights()
        
        # 移动到设备
        self.to_device()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        x = self.features(x)
        x = self.classifier(x)
        return x
    
    def _initialize_weights(self):
        """初始化权重"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = super().get_model_info()
        base_info.update({
            'model_type': 'EfficientSceneNet',
            'width_multiplier': self.width_multiplier,
            'architecture': 'Efficient CNN for Game Scene Classification'
        })
        return base_info


# === 便捷函数 ===

def create_scene_classifier(model_type: str = 'GameSceneNet',
                          num_classes: int = 10,
                          **kwargs) -> BaseGameClassifier:
    """
    创建场景分类器的便捷函数
    
    Args:
        model_type: 模型类型 ('GameSceneNet', 'ResNet', 'Efficient')
        num_classes: 类别数
        **kwargs: 其他参数
        
    Returns:
        场景分类器实例
    """
    if model_type.lower() in ['gamescenenet', 'default']:
        return GameSceneNet(num_classes=num_classes, **kwargs)
    elif model_type.lower() in ['resnet', 'resnet18']:
        return ResNetSceneClassifier(num_classes=num_classes, **kwargs)
    elif model_type.lower() in ['efficient', 'efficientnet']:
        return EfficientSceneNet(num_classes=num_classes, **kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


def load_scene_classifier(checkpoint_path: str,
                         model_type: str = 'GameSceneNet', 
                         num_classes: int = 10,
                         **kwargs) -> BaseGameClassifier:
    """
    从检查点加载场景分类器
    
    Args:
        checkpoint_path: 检查点文件路径
        model_type: 模型类型
        num_classes: 类别数
        **kwargs: 其他参数
        
    Returns:
        加载权重后的分类器
    """
    model = create_scene_classifier(model_type, num_classes, **kwargs)
    model.load_weights(checkpoint_path)
    return model

