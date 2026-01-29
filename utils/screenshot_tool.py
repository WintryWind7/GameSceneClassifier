"""
GameSceneClassifier 截图工具主模块

整合窗口捕获、GUI界面和快捷键系统的完整截图工具
"""

import os
import sys
import threading
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .window_capture import WindowCapture, WindowInfo
from .hotkey_manager import HotkeyManager
from .capture_gui import CaptureGUI


class ScreenshotTool:
    """完整的截图工具类"""
    
    def __init__(self, 
                 save_directory: Optional[str] = None,
                 auto_save: bool = True,
                 default_hotkey: str = "F9"):
        """
        初始化截图工具
        
        Args:
            save_directory: 保存目录，默认为当前目录下的screenshots
            auto_save: 是否自动保存
            default_hotkey: 默认快捷键
        """
        # 核心组件
        self.window_capture = WindowCapture()
        self.hotkey_manager = HotkeyManager()
        
        # 配置
        self.save_directory = save_directory or os.path.join(os.getcwd(), "screenshots")
        self.auto_save = auto_save
        self.default_hotkey = default_hotkey
        
        # 状态
        self.target_window = None
        self.is_initialized = False
        
        # 回调函数
        self.on_capture_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # 确保保存目录存在
        os.makedirs(self.save_directory, exist_ok=True)
    
    def initialize(self):
        """初始化截图工具"""
        if self.is_initialized:
            return
        
        try:
            # 启动快捷键监听
            self.hotkey_manager.start()
            
            # 设置默认快捷键
            self.set_hotkey(self.default_hotkey)
            
            self.is_initialized = True
            print(f"截图工具已初始化")
            print(f"保存目录: {self.save_directory}")
            print(f"默认快捷键: {self.default_hotkey}")
            
        except Exception as e:
            print(f"初始化截图工具失败: {e}")
            raise
    
    def set_target_window_by_title(self, title: str, exact_match: bool = False) -> bool:
        """
        根据标题设置目标窗口
        
        Args:
            title: 窗口标题
            exact_match: 是否精确匹配
            
        Returns:
            是否设置成功
        """
        window = self.window_capture.find_window_by_title(title, exact_match)
        if window:
            self.target_window = window
            self.window_capture.set_target_window(window)
            print(f"已设置目标窗口: {window.title}")
            return True
        else:
            print(f"未找到窗口: {title}")
            return False
    
    def set_target_window(self, window: WindowInfo):
        """设置目标窗口"""
        self.target_window = window
        self.window_capture.set_target_window(window)
        print(f"已设置目标窗口: {window.title}")
    
    def get_available_windows(self):
        """获取可用窗口列表"""
        return self.window_capture.get_all_windows()
    
    def set_hotkey(self, hotkey: str) -> bool:
        """
        设置截图快捷键
        
        Args:
            hotkey: 快捷键字符串
            
        Returns:
            是否设置成功
        """
        try:
            # 移除旧的快捷键
            self.hotkey_manager.remove_all_hotkeys()
            
            # 添加新的快捷键
            success = self.hotkey_manager.add_hotkey(hotkey, self._hotkey_capture)
            
            if success:
                self.default_hotkey = hotkey
                print(f"快捷键已设置为: {hotkey}")
            else:
                print(f"设置快捷键失败: {hotkey}")
            
            return success
            
        except Exception as e:
            print(f"设置快捷键出错: {e}")
            return False
    
    def _hotkey_capture(self):
        """快捷键触发的截图"""
        try:
            self.capture_screenshot()
        except Exception as e:
            print(f"快捷键截图失败: {e}")
            if self.on_error_callback:
                self.on_error_callback(e)
    
    def capture_screenshot(self, save_file: bool = None) -> Optional[str]:
        """
        捕获截图
        
        Args:
            save_file: 是否保存文件，None则使用auto_save设置
            
        Returns:
            保存的文件路径或None
        """
        if not self.target_window:
            error_msg = "未设置目标窗口"
            print(f"截图失败: {error_msg}")
            if self.on_error_callback:
                self.on_error_callback(error_msg)
            return None
        
        try:
            # 捕获窗口
            img = self.window_capture.capture_window(self.target_window)
            
            if img is None:
                error_msg = "窗口捕获失败"
                print(f"截图失败: {error_msg}")
                if self.on_error_callback:
                    self.on_error_callback(error_msg)
                return None
            
            filepath = None
            
            # 保存文件
            should_save = save_file if save_file is not None else self.auto_save
            if should_save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(self.save_directory, filename)
                
                success = self.window_capture.capture_to_file(filepath, self.target_window)
                if success:
                    print(f"截图已保存: {filename}")
                else:
                    print("保存截图失败")
                    filepath = None
            
            # 调用回调函数
            if self.on_capture_callback:
                self.on_capture_callback(img, filepath)
            
            return filepath
            
        except Exception as e:
            print(f"截图过程出错: {e}")
            if self.on_error_callback:
                self.on_error_callback(e)
            return None
    
    def set_capture_callback(self, callback: Callable):
        """
        设置截图回调函数
        
        Args:
            callback: 回调函数，接收 (image, filepath) 参数
        """
        self.on_capture_callback = callback
    
    def set_error_callback(self, callback: Callable):
        """
        设置错误回调函数
        
        Args:
            callback: 回调函数，接收错误信息参数
        """
        self.on_error_callback = callback
    
    def start_continuous_capture(self, interval: float = 1.0) -> threading.Thread:
        """
        开始连续截图
        
        Args:
            interval: 截图间隔（秒）
            
        Returns:
            截图线程
        """
        def capture_callback(img):
            if self.auto_save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"continuous_{timestamp}.png"
                filepath = os.path.join(self.save_directory, filename)
                
                import cv2
                cv2.imwrite(filepath, img)
            
            if self.on_capture_callback:
                self.on_capture_callback(img, filepath if self.auto_save else None)
        
        return self.window_capture.start_continuous_capture(interval, capture_callback)
    
    def stop_continuous_capture(self):
        """停止连续截图"""
        self.window_capture.stop_continuous_capture()
    
    def get_status(self) -> Dict[str, Any]:
        """获取工具状态"""
        return {
            'initialized': self.is_initialized,
            'target_window': self.target_window.title if self.target_window else None,
            'save_directory': self.save_directory,
            'auto_save': self.auto_save,
            'hotkey': self.default_hotkey,
            'hotkey_active': self.hotkey_manager.is_active(),
            'registered_hotkeys': self.hotkey_manager.get_registered_hotkeys()
        }
    
    def cleanup(self):
        """清理资源"""
        try:
            self.hotkey_manager.stop()
            self.window_capture.stop_continuous_capture()
            print("截图工具已清理")
        except Exception as e:
            print(f"清理资源时出错: {e}")
    
    def launch_gui(self):
        """启动GUI界面"""
        try:
            gui = CaptureGUI()
            gui.run()
        except Exception as e:
            print(f"启动GUI失败: {e}")
            raise


# === 便捷函数 ===

def create_screenshot_tool(**kwargs) -> ScreenshotTool:
    """
    创建截图工具实例
    
    Args:
        **kwargs: 传递给ScreenshotTool的参数
        
    Returns:
        截图工具实例
    """
    tool = ScreenshotTool(**kwargs)
    tool.initialize()
    return tool


def quick_screenshot(window_title: str, 
                    save_directory: Optional[str] = None,
                    hotkey: str = "F9") -> ScreenshotTool:
    """
    快速设置截图工具
    
    Args:
        window_title: 目标窗口标题
        save_directory: 保存目录
        hotkey: 快捷键
        
    Returns:
        配置好的截图工具
    """
    tool = create_screenshot_tool(
        save_directory=save_directory,
        default_hotkey=hotkey
    )
    
    if tool.set_target_window_by_title(window_title):
        print(f"截图工具已就绪，按 {hotkey} 截图")
        return tool
    else:
        print(f"未找到窗口: {window_title}")
        print("可用窗口:")
        windows = tool.get_available_windows()
        for i, window in enumerate(windows[:10]):  # 只显示前10个
            print(f"  {i+1}. {window.title}")
        
        return tool


def launch_screenshot_gui():
    """启动截图器GUI"""
    try:
        gui = CaptureGUI()
        gui.run()
    except Exception as e:
        print(f"启动截图器GUI失败: {e}")
        import traceback
        traceback.print_exc()


def interactive_screenshot_setup():
    """交互式截图工具设置"""
    print("=== GameSceneClassifier 截图工具 ===")
    
    # 获取可用窗口
    tool = ScreenshotTool()
    windows = tool.get_available_windows()
    
    if not windows:
        print("未找到可用窗口")
        return None
    
    # 显示窗口列表
    print("\n可用窗口:")
    for i, window in enumerate(windows):
        size = window.get_size()
        print(f"  {i+1}. {window.title} ({size[0]}x{size[1]})")
    
    # 用户选择
    try:
        choice = int(input(f"\n请选择窗口 (1-{len(windows)}): ")) - 1
        if 0 <= choice < len(windows):
            selected_window = windows[choice]
        else:
            print("无效选择")
            return None
    except ValueError:
        print("无效输入")
        return None
    
    # 设置快捷键
    hotkey = input("请输入快捷键 (默认 F9): ").strip() or "F9"
    
    # 创建工具
    tool = create_screenshot_tool(default_hotkey=hotkey)
    tool.set_target_window(selected_window)
    
    print(f"\n截图工具已设置:")
    print(f"  目标窗口: {selected_window.title}")
    print(f"  快捷键: {hotkey}")
    print(f"  保存目录: {tool.save_directory}")
    print(f"\n按 {hotkey} 开始截图，按 Ctrl+C 退出")
    
    return tool


if __name__ == "__main__":
    # 命令行使用示例
    if len(sys.argv) > 1:
        if sys.argv[1] == "gui":
            launch_screenshot_gui()
        elif sys.argv[1] == "interactive":
            tool = interactive_screenshot_setup()
            if tool:
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n正在退出...")
                    tool.cleanup()
        else:
            print("用法:")
            print("  python screenshot_tool.py gui         # 启动GUI")
            print("  python screenshot_tool.py interactive # 交互式设置")
    else:
        launch_screenshot_gui()
