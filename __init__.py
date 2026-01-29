"""
GameSceneClassifier

专用于游戏场景分类的深度学习框架
参考Ultralytics YOLO的优秀设计理念，提供简洁易用的API
"""

from .model import (
    BaseGameClassifier,
    GameSceneNet,
    ResNetSceneClassifier,
    EfficientSceneNet,
    create_scene_classifier,
    load_scene_classifier,
    GameSceneDataset,
    GameDataLoader,
    GameDataManager,
    create_game_dataset,
    create_data_manager
)

# 主要导出类 - 效仿 "from ultralytics import YOLO" 的设计
# 用户可以 "from GameSceneClassifier import GSC"
GSC = GameSceneNet

__version__ = "0.1.0"
__author__ = "GameSceneClassifier Team"

__all__ = [
    # 主要接口
    'GSC',  # 主要的分类器类
    
    # 网络架构
    'BaseGameClassifier',
    'GameSceneNet',
    'ResNetSceneClassifier',
    'EfficientSceneNet',
    'create_scene_classifier',
    'load_scene_classifier',
    
    # 数据处理
    'GameSceneDataset',
    'GameDataLoader',
    'GameDataManager',
    'create_game_dataset',
    'create_data_manager',
    
    # 版本信息
    '__version__',
    '__author__',
]

