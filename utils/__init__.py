"""
GameSceneClassifier Utils Module

工具函数模块 - 包括截图工具、数据集构建工具等
"""

# 窗口捕获相关
from .window_capture import (
    WindowCapture,
    WindowInfo,
    get_window_list,
    capture_window_by_title,
    quick_window_capture,
    test_window_detection
)

# 快捷键管理
from .hotkey_manager import (
    HotkeyManager,
    create_hotkey_manager
)

# GUI界面
from .capture_gui import (
    CaptureGUI,
    launch_capture_gui
)

# 完整截图工具
from .screenshot_tool import (
    ScreenshotTool,
    create_screenshot_tool,
    quick_screenshot,
    launch_screenshot_gui,
    interactive_screenshot_setup
)

__all__ = [
    # 窗口捕获
    'WindowCapture',
    'WindowInfo',
    'get_window_list',
    'capture_window_by_title',
    'quick_window_capture',
    'test_window_detection',

    # 快捷键管理
    'HotkeyManager',
    'create_hotkey_manager',

    # GUI界面
    'CaptureGUI',
    'launch_capture_gui',

    # 完整截图工具
    'ScreenshotTool',
    'create_screenshot_tool',
    'quick_screenshot',
    'launch_screenshot_gui',
    'interactive_screenshot_setup',
]

