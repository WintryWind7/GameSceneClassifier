"""
GameSceneClassifier 快捷键管理器

提供全局快捷键监听和管理功能
"""

import threading
import time
from typing import Dict, Callable, Optional, Set, List
import win32api
import win32con
import win32gui
from collections import defaultdict


class HotkeyManager:
    """全局快捷键管理器"""
    
    # 虚拟键码映射
    VK_CODE_MAP = {
        # 功能键
        'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73,
        'F5': 0x74, 'F6': 0x75, 'F7': 0x76, 'F8': 0x77,
        'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
        
        # 数字键
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        
        # 字母键
        'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45,
        'F': 0x46, 'G': 0x47, 'H': 0x48, 'I': 0x49, 'J': 0x4A,
        'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E, 'O': 0x4F,
        'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54,
        'U': 0x55, 'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59,
        'Z': 0x5A,
        
        # 修饰键
        'CTRL': 0x11, 'ALT': 0x12, 'SHIFT': 0x10,
        'WIN': 0x5B, 'LWIN': 0x5B, 'RWIN': 0x5C,
        
        # 特殊键
        'SPACE': 0x20, 'ENTER': 0x0D, 'ESC': 0x1B, 'TAB': 0x09,
        'BACKSPACE': 0x08, 'DELETE': 0x2E, 'INSERT': 0x2D,
        'HOME': 0x24, 'END': 0x23, 'PAGEUP': 0x21, 'PAGEDOWN': 0x22,
        
        # 方向键
        'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
        
        # 数字键盘
        'NUMPAD0': 0x60, 'NUMPAD1': 0x61, 'NUMPAD2': 0x62, 'NUMPAD3': 0x63,
        'NUMPAD4': 0x64, 'NUMPAD5': 0x65, 'NUMPAD6': 0x66, 'NUMPAD7': 0x67,
        'NUMPAD8': 0x68, 'NUMPAD9': 0x69,
        
        # 符号键
        'PLUS': 0xBB, 'MINUS': 0xBD, 'MULTIPLY': 0x6A, 'DIVIDE': 0x6F,
    }
    
    def __init__(self):
        self.hotkeys: Dict[str, Callable] = {}
        self.key_states: Dict[int, bool] = defaultdict(bool)
        self.is_running = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # 快捷键组合状态
        self.pressed_keys: Set[int] = set()
        self.last_trigger_time = defaultdict(float)
        self.trigger_cooldown = 0.2  # 200ms冷却时间
    
    def parse_hotkey(self, hotkey_str: str) -> List[int]:
        """
        解析快捷键字符串为虚拟键码列表
        
        Args:
            hotkey_str: 快捷键字符串，如 "Ctrl+F9", "Alt+Shift+S"
            
        Returns:
            虚拟键码列表
        """
        if not hotkey_str:
            return []
        
        # 分割快捷键组合
        keys = [key.strip().upper() for key in hotkey_str.split('+')]
        vk_codes = []
        
        for key in keys:
            if key in self.VK_CODE_MAP:
                vk_codes.append(self.VK_CODE_MAP[key])
            else:
                print(f"警告: 未知的按键 '{key}'")
        
        return vk_codes
    
    def add_hotkey(self, hotkey_str: str, callback: Callable) -> bool:
        """
        添加快捷键
        
        Args:
            hotkey_str: 快捷键字符串
            callback: 回调函数
            
        Returns:
            是否添加成功
        """
        try:
            vk_codes = self.parse_hotkey(hotkey_str)
            if not vk_codes:
                print(f"无效的快捷键: {hotkey_str}")
                return False
            
            with self.lock:
                # 将虚拟键码列表转换为字符串作为键
                key = ','.join(map(str, sorted(vk_codes)))
                self.hotkeys[key] = callback
            
            print(f"已添加快捷键: {hotkey_str} -> {key}")
            return True
            
        except Exception as e:
            print(f"添加快捷键失败: {e}")
            return False
    
    def remove_hotkey(self, hotkey_str: str) -> bool:
        """
        移除快捷键
        
        Args:
            hotkey_str: 快捷键字符串
            
        Returns:
            是否移除成功
        """
        try:
            vk_codes = self.parse_hotkey(hotkey_str)
            if not vk_codes:
                return False
            
            with self.lock:
                key = ','.join(map(str, sorted(vk_codes)))
                if key in self.hotkeys:
                    del self.hotkeys[key]
                    print(f"已移除快捷键: {hotkey_str}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"移除快捷键失败: {e}")
            return False
    
    def remove_all_hotkeys(self):
        """移除所有快捷键"""
        with self.lock:
            self.hotkeys.clear()
            print("已移除所有快捷键")
    
    def is_key_pressed(self, vk_code: int) -> bool:
        """检查按键是否被按下"""
        try:
            state = win32api.GetAsyncKeyState(vk_code)
            return (state & 0x8000) != 0
        except:
            return False
    
    def check_hotkey_combination(self, vk_codes: List[int]) -> bool:
        """检查快捷键组合是否被按下"""
        if not vk_codes:
            return False
        
        # 检查所有按键是否都被按下
        for vk_code in vk_codes:
            if not self.is_key_pressed(vk_code):
                return False
        
        return True
    
    def _monitor_keys(self):
        """监控按键状态的主循环"""
        print("快捷键监听已启动")
        
        while self.is_running:
            try:
                current_time = time.time()
                
                with self.lock:
                    hotkeys_copy = self.hotkeys.copy()
                
                # 检查每个快捷键组合
                for key_combination, callback in hotkeys_copy.items():
                    try:
                        vk_codes = [int(code) for code in key_combination.split(',')]
                        
                        # 检查快捷键是否被按下
                        if self.check_hotkey_combination(vk_codes):
                            # 检查冷却时间
                            if current_time - self.last_trigger_time[key_combination] > self.trigger_cooldown:
                                self.last_trigger_time[key_combination] = current_time
                                
                                # 在新线程中执行回调，避免阻塞监听
                                threading.Thread(target=self._safe_callback, 
                                               args=(callback, key_combination), 
                                               daemon=True).start()
                    
                    except Exception as e:
                        print(f"检查快捷键 {key_combination} 时出错: {e}")
                
                # 短暂休眠以减少CPU使用率
                time.sleep(0.01)  # 10ms
                
            except Exception as e:
                print(f"快捷键监听出错: {e}")
                time.sleep(0.1)
        
        print("快捷键监听已停止")
    
    def _safe_callback(self, callback: Callable, key_combination: str):
        """安全地执行回调函数"""
        try:
            callback()
        except Exception as e:
            print(f"快捷键回调执行失败 ({key_combination}): {e}")
    
    def start(self):
        """启动快捷键监听"""
        if self.is_running:
            print("快捷键监听已经在运行")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_keys, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """停止快捷键监听"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        print("快捷键监听已停止")
    
    def is_active(self) -> bool:
        """检查快捷键监听是否活跃"""
        return self.is_running and self.monitor_thread and self.monitor_thread.is_alive()
    
    def get_registered_hotkeys(self) -> List[str]:
        """获取已注册的快捷键列表"""
        with self.lock:
            hotkeys = []
            for key_combination in self.hotkeys.keys():
                vk_codes = [int(code) for code in key_combination.split(',')]
                # 尝试反向解析为可读字符串
                key_names = []
                for vk_code in vk_codes:
                    for name, code in self.VK_CODE_MAP.items():
                        if code == vk_code:
                            key_names.append(name)
                            break
                    else:
                        key_names.append(f"VK_{vk_code}")
                
                hotkeys.append('+'.join(key_names))
            
            return hotkeys


# === 便捷函数 ===

def create_hotkey_manager() -> HotkeyManager:
    """创建快捷键管理器"""
    return HotkeyManager()


def test_hotkey_system():
    """测试快捷键系统"""
    def test_callback():
        print("快捷键被触发!")
    
    manager = HotkeyManager()
    
    # 添加测试快捷键
    manager.add_hotkey("F9", test_callback)
    manager.add_hotkey("Ctrl+F10", test_callback)
    
    # 启动监听
    manager.start()
    
    print("快捷键测试已启动，按 F9 或 Ctrl+F10 测试")
    print("按 Ctrl+C 退出")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在退出...")
        manager.stop()


if __name__ == "__main__":
    test_hotkey_system()
