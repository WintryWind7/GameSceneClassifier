"""
GameSceneClassifier 窗口捕获模块

提供Windows窗口捕获功能，支持指定窗口截图
"""

import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image
from typing import List, Tuple, Optional, Dict, Any
import time
import threading


class WindowInfo:
    """窗口信息类"""
    
    def __init__(self, hwnd: int, title: str, class_name: str = ""):
        self.hwnd = hwnd
        self.title = title
        self.class_name = class_name
        self.rect = None
        self._update_rect()
    
    def _update_rect(self):
        """更新窗口矩形区域"""
        try:
            self.rect = win32gui.GetWindowRect(self.hwnd)
        except:
            self.rect = (0, 0, 0, 0)
    
    def get_size(self) -> Tuple[int, int]:
        """获取窗口尺寸"""
        if self.rect:
            return (self.rect[2] - self.rect[0], self.rect[3] - self.rect[1])
        return (0, 0)
    
    def is_visible(self) -> bool:
        """检查窗口是否可见"""
        try:
            return win32gui.IsWindowVisible(self.hwnd)
        except:
            return False
    
    def is_minimized(self) -> bool:
        """检查窗口是否最小化"""
        try:
            return win32gui.IsIconic(self.hwnd)
        except:
            return False
    
    def __str__(self) -> str:
        return f"Window('{self.title}', {self.get_size()})"


class WindowCapture:
    """Windows窗口捕获器"""
    
    def __init__(self):
        self.target_window = None
        self.capture_region = None  # (x, y, width, height)
        
    def get_all_windows(self, include_invisible: bool = False) -> List[WindowInfo]:
        """
        获取所有窗口列表
        
        Args:
            include_invisible: 是否包含不可见窗口
            
        Returns:
            窗口信息列表
        """
        windows = []
        
        def enum_windows_callback(hwnd, windows_list):
            try:
                if win32gui.IsWindow(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    # 基本过滤：有标题的窗口
                    if title.strip() and len(title) > 1:
                        window_info = WindowInfo(hwnd, title, class_name)
                        
                        if not include_invisible:
                            # 只包含在任务栏显示的窗口
                            # 检查窗口是否有WS_EX_APPWINDOW样式或者没有父窗口且可见
                            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                            parent = win32gui.GetParent(hwnd)
                            
                            # 任务栏窗口的条件：
                            # 1. 有WS_EX_APPWINDOW样式，或者
                            # 2. 没有父窗口且可见且不是工具窗口
                            is_app_window = (ex_style & win32con.WS_EX_APPWINDOW) != 0
                            is_tool_window = (ex_style & win32con.WS_EX_TOOLWINDOW) != 0
                            is_visible = window_info.is_visible()
                            has_no_parent = parent == 0
                            
                            if is_app_window or (has_no_parent and is_visible and not is_tool_window):
                                windows_list.append(window_info)
                        else:
                            windows_list.append(window_info)
            except Exception:
                pass
            
            return True
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        # 按标题排序
        windows.sort(key=lambda w: w.title.lower())
        
        return windows
    
    def find_window_by_title(self, title: str, exact_match: bool = False) -> Optional[WindowInfo]:
        """
        根据标题查找窗口
        
        Args:
            title: 窗口标题
            exact_match: 是否精确匹配
            
        Returns:
            窗口信息或None
        """
        windows = self.get_all_windows()
        
        for window in windows:
            if exact_match:
                if window.title == title:
                    return window
            else:
                if title.lower() in window.title.lower():
                    return window
        
        return None
    
    def set_target_window(self, window: WindowInfo):
        """设置目标窗口"""
        self.target_window = window
        print(f"设置目标窗口: {window.title}")
    
    def set_capture_region(self, x: int, y: int, width: int, height: int):
        """
        设置捕获区域（相对于窗口）
        
        Args:
            x, y: 区域左上角坐标
            width, height: 区域尺寸
        """
        self.capture_region = (x, y, width, height)
        print(f"设置捕获区域: ({x}, {y}, {width}, {height})")
    
    def capture_window(self, window: Optional[WindowInfo] = None) -> Optional[np.ndarray]:
        """
        捕获指定窗口
        
        Args:
            window: 窗口信息，如果为None则使用当前目标窗口
            
        Returns:
            捕获的图像数组 (BGR格式) 或 None
        """
        target = window or self.target_window
        
        if not target:
            print("错误: 没有设置目标窗口")
            return None
        
        # 尝试多种截图方法
        methods = [
            self._capture_with_printwindow,
            self._capture_with_bitblt,
            self._capture_with_desktop_duplication
        ]
        
        for i, method in enumerate(methods):
            try:
                print(f"尝试截图方法 {i+1}...")
                result = method(target)
                if result is not None:
                    print(f"截图方法 {i+1} 成功")
                    return result
                else:
                    print(f"截图方法 {i+1} 返回空结果")
            except Exception as e:
                print(f"截图方法 {i+1} 失败: {e}")
                continue
        
        print("所有截图方法都失败了")
        return None
    
    def _capture_with_printwindow(self, target: WindowInfo) -> Optional[np.ndarray]:
        """使用PrintWindow API截图"""
        hwnd = target.hwnd
        
        # 检查窗口是否仍然存在
        if not win32gui.IsWindow(hwnd):
            raise Exception("窗口不存在")
        
        # 获取窗口矩形
        window_rect = win32gui.GetWindowRect(hwnd)
        width = window_rect[2] - window_rect[0]
        height = window_rect[3] - window_rect[1]
        
        if width <= 0 or height <= 0:
            raise Exception(f"窗口尺寸无效: {width}x{height}")
        
        # 获取窗口设备上下文
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        if not hwnd_dc:
            raise Exception("无法获取窗口设备上下文")
        
        try:
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # 创建位图
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # 使用PrintWindow捕获窗口内容
            result = win32gui.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
            
            if result == 0:
                raise Exception("PrintWindow调用失败")
            
            # 获取位图数据
            bmp_str = save_bitmap.GetBitmapBits(True)
            
            # 转换为numpy数组
            img_array = np.frombuffer(bmp_str, dtype=np.uint8)
            img_array = img_array.reshape((height, width, 4))  # BGRA格式
            
            # 转换为BGR格式
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
            
            # 清理资源
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            
            return self._apply_capture_region(img_bgr)
            
        finally:
            win32gui.ReleaseDC(hwnd, hwnd_dc)
    
    def _capture_with_bitblt(self, target: WindowInfo) -> Optional[np.ndarray]:
        """使用BitBlt API截图"""
        hwnd = target.hwnd
        
        # 检查窗口是否存在
        if not win32gui.IsWindow(hwnd):
            raise Exception("窗口不存在")
        
        # 获取窗口矩形
        window_rect = win32gui.GetWindowRect(hwnd)
        width = window_rect[2] - window_rect[0]
        height = window_rect[3] - window_rect[1]
        
        if width <= 0 or height <= 0:
            raise Exception(f"窗口尺寸无效: {width}x{height}")
        
        # 获取窗口设备上下文
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        if not hwnd_dc:
            raise Exception("无法获取窗口设备上下文")
        
        try:
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # 创建位图
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # 使用BitBlt复制窗口内容
            result = save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
            
            if result == 0:
                raise Exception("BitBlt调用失败")
            
            # 获取位图数据
            bmp_str = save_bitmap.GetBitmapBits(True)
            
            # 转换为numpy数组
            img_array = np.frombuffer(bmp_str, dtype=np.uint8)
            img_array = img_array.reshape((height, width, 4))  # BGRA格式
            
            # 转换为BGR格式
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
            
            # 清理资源
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            
            return self._apply_capture_region(img_bgr)
            
        finally:
            win32gui.ReleaseDC(hwnd, hwnd_dc)
    
    def _capture_with_desktop_duplication(self, target: WindowInfo) -> Optional[np.ndarray]:
        """使用桌面复制API截图（适用于某些特殊窗口）"""
        try:
            import mss
            
            # 获取窗口位置
            window_rect = win32gui.GetWindowRect(target.hwnd)
            
            # 使用mss库截取屏幕区域
            with mss.mss() as sct:
                monitor = {
                    "top": window_rect[1],
                    "left": window_rect[0], 
                    "width": window_rect[2] - window_rect[0],
                    "height": window_rect[3] - window_rect[1]
                }
                
                screenshot = sct.grab(monitor)
                img_array = np.array(screenshot)
                
                # 转换颜色格式 (BGRA -> BGR)
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                
                return self._apply_capture_region(img_bgr)
                
        except ImportError:
            # mss库未安装，跳过此方法
            raise Exception("mss库未安装，无法使用桌面复制API")
        except Exception as e:
            raise Exception(f"桌面复制API失败: {e}")
    
    def _apply_capture_region(self, img: np.ndarray) -> np.ndarray:
        """应用捕获区域裁剪"""
        if self.capture_region and img is not None:
            height, width = img.shape[:2]
            x, y, crop_width, crop_height = self.capture_region
            
            # 确保裁剪区域在图像范围内
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            crop_width = min(crop_width, width - x)
            crop_height = min(crop_height, height - y)
            
            if crop_width > 0 and crop_height > 0:
                img = img[y:y+crop_height, x:x+crop_width]
        
        return img
    
    def capture_to_file(self, filename: str, window: Optional[WindowInfo] = None) -> bool:
        """
        捕获窗口并保存到文件
        
        Args:
            filename: 保存文件名
            window: 窗口信息
            
        Returns:
            是否成功
        """
        img = self.capture_window(window)
        if img is not None:
            try:
                cv2.imwrite(filename, img)
                print(f"截图已保存: {filename}")
                return True
            except Exception as e:
                print(f"保存截图失败: {e}")
                return False
        return False
    
    def get_window_screenshot_pil(self, window: Optional[WindowInfo] = None) -> Optional[Image.Image]:
        """
        获取窗口截图的PIL图像
        
        Args:
            window: 窗口信息
            
        Returns:
            PIL图像或None
        """
        img = self.capture_window(window)
        if img is not None:
            # BGR转RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(img_rgb)
        return None
    
    def start_continuous_capture(self, interval: float = 1.0, 
                                callback: Optional[callable] = None) -> threading.Thread:
        """
        开始连续捕获
        
        Args:
            interval: 捕获间隔（秒）
            callback: 回调函数，接收捕获的图像
            
        Returns:
            捕获线程
        """
        self._stop_capture = False
        
        def capture_loop():
            while not self._stop_capture:
                img = self.capture_window()
                if img is not None and callback:
                    callback(img)
                time.sleep(interval)
        
        thread = threading.Thread(target=capture_loop, daemon=True)
        thread.start()
        return thread
    
    def stop_continuous_capture(self):
        """停止连续捕获"""
        self._stop_capture = True
    
    def get_target_window_info(self) -> Dict[str, Any]:
        """获取目标窗口信息"""
        if not self.target_window:
            return {}
        
        return {
            'title': self.target_window.title,
            'class_name': self.target_window.class_name,
            'size': self.target_window.get_size(),
            'visible': self.target_window.is_visible(),
            'minimized': self.target_window.is_minimized(),
            'capture_region': self.capture_region
        }


# === 便捷函数 ===

def get_window_list() -> List[WindowInfo]:
    """获取所有可用窗口列表"""
    capture = WindowCapture()
    return capture.get_all_windows()


def capture_window_by_title(title: str, filename: Optional[str] = None) -> Optional[np.ndarray]:
    """
    根据窗口标题捕获窗口
    
    Args:
        title: 窗口标题
        filename: 可选的保存文件名
        
    Returns:
        捕获的图像或None
    """
    capture = WindowCapture()
    window = capture.find_window_by_title(title)
    
    if not window:
        print(f"未找到窗口: {title}")
        return None
    
    img = capture.capture_window(window)
    
    if img is not None and filename:
        cv2.imwrite(filename, img)
        print(f"截图已保存: {filename}")
    
    return img


def quick_window_capture(window_title: str = "") -> Optional[Image.Image]:
    """
    快速窗口捕获，返回PIL图像
    
    Args:
        window_title: 窗口标题，为空则显示窗口选择
        
    Returns:
        PIL图像或None
    """
    capture = WindowCapture()
    
    if window_title:
        window = capture.find_window_by_title(window_title)
    else:
        # 显示可用窗口列表
        windows = capture.get_all_windows()
        if not windows:
            print("没有找到可用窗口")
            return None
        
        print("可用窗口:")
        for i, window in enumerate(windows):
            print(f"{i+1}. {window.title}")
        
        try:
            choice = int(input("请选择窗口 (输入数字): ")) - 1
            if 0 <= choice < len(windows):
                window = windows[choice]
            else:
                print("无效选择")
                return None
        except ValueError:
            print("无效输入")
            return None
    
    if window:
        return capture.get_window_screenshot_pil(window)
    
    return None


def test_window_detection():
    """
    测试窗口获取功能 - 获取并打印前台窗口
    前台窗口 = 用户当前能看到的、在屏幕前台显示的窗口
    Returns:
        获取到的前台窗口列表
    """
    print("前台窗口获取功能测试")
    print("=" * 60)
    
    try:
        capture = WindowCapture()
        
        # 获取前台窗口
        print("正在获取前台窗口...")
        visible_windows = capture.get_all_windows(include_invisible=False)
        
        if not visible_windows:
            print("❌ 没有获取到任何前台窗口")
            return []
        
        print(f"✅ 成功获取到 {len(visible_windows)} 个前台窗口\n")
        
        # 打印所有前台窗口信息
        for i, window in enumerate(visible_windows, 1):
            try:
                size = window.get_size()
                
                print(f"{i:3d}. {window.title}")
                print(f"     类名: {window.class_name}")
                print(f"     句柄: {window.hwnd}")
                print(f"     尺寸: {size[0]}x{size[1]}")
                print()
                
            except Exception as e:
                print(f"{i:3d}. {window.title} [获取信息失败: {e}]")
                print()
        
        print("=" * 60)
        print(f"获取到 {len(visible_windows)} 个前台窗口")
        
        return visible_windows
        
    except Exception as e:
        print(f"❌ 窗口获取失败: {e}")
        return []
