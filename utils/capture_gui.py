"""
GameSceneClassifier 截图器GUI界面

提供用户友好的截图器图形界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
from datetime import datetime
from typing import Optional, Callable, List
import cv2
import numpy as np
from PIL import Image, ImageTk

from .window_capture import WindowCapture, WindowInfo
from .hotkey_manager import HotkeyManager


class CaptureGUI:
    """截图器GUI主界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GameSceneClassifier - 游戏截图器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 核心组件
        self.window_capture = WindowCapture()
        self.hotkey_manager = HotkeyManager()
        
        # 状态变量
        self.selected_window = None
        self.save_directory = os.path.join(os.getcwd(), "screenshots")
        self.auto_save = tk.BooleanVar(value=True)
        self.capture_hotkey = tk.StringVar(value="F9")
        self.is_capturing = False
        
        # 创建保存目录
        os.makedirs(self.save_directory, exist_ok=True)
        
        # 构建界面
        self._create_widgets()
        self._setup_hotkeys()
        
        # 刷新窗口列表
        self.refresh_windows()
    
    def _create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === 窗口选择区域 ===
        window_frame = ttk.LabelFrame(main_frame, text="窗口选择", padding="5")
        window_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        window_frame.columnconfigure(1, weight=1)
        
        # 刷新按钮
        ttk.Button(window_frame, text="刷新窗口列表", 
                  command=self.refresh_windows).grid(row=0, column=0, padx=(0, 10))
        
        # 窗口选择下拉框
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, 
                                        state="readonly", width=50)
        self.window_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.window_combo.bind('<<ComboboxSelected>>', self.on_window_selected)
        
        # === 捕获设置区域 ===
        settings_frame = ttk.LabelFrame(main_frame, text="捕获设置", padding="5")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 快捷键设置
        ttk.Label(settings_frame, text="捕获快捷键:").grid(row=0, column=0, sticky=tk.W)
        hotkey_frame = ttk.Frame(settings_frame)
        hotkey_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.hotkey_entry = ttk.Entry(hotkey_frame, textvariable=self.capture_hotkey, width=10)
        self.hotkey_entry.grid(row=0, column=0)
        ttk.Button(hotkey_frame, text="设置", 
                  command=self.update_hotkey).grid(row=0, column=1, padx=(5, 0))
        
        # 自动保存选项
        ttk.Checkbutton(settings_frame, text="自动保存截图", 
                       variable=self.auto_save).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 保存目录设置
        ttk.Label(settings_frame, text="保存目录:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(5, 0))
        dir_frame.columnconfigure(0, weight=1)
        
        self.dir_var = tk.StringVar(value=self.save_directory)
        ttk.Entry(dir_frame, textvariable=self.dir_var, state="readonly").grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="浏览", 
                  command=self.browse_directory).grid(row=0, column=1, padx=(5, 0))
        
        # === 控制按钮区域 ===
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # 立即截图按钮
        self.capture_btn = ttk.Button(control_frame, text="立即截图 (F9)", 
                                     command=self.manual_capture, style="Accent.TButton")
        self.capture_btn.grid(row=0, column=0, padx=(0, 10))
        
        # 预览按钮
        ttk.Button(control_frame, text="预览窗口", 
                  command=self.preview_window).grid(row=0, column=1, padx=(0, 10))
        
        # 打开保存目录按钮
        ttk.Button(control_frame, text="打开保存目录", 
                  command=self.open_save_directory).grid(row=0, column=2)
        
        # === 状态和预览区域 ===
        preview_frame = ttk.LabelFrame(main_frame, text="预览和状态", padding="5")
        preview_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪 - 请选择窗口")
        self.status_label = ttk.Label(preview_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 预览画布
        self.preview_canvas = tk.Canvas(preview_frame, bg="gray90", height=200)
        self.preview_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # 滚动条
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_canvas.yview)
        preview_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)
        
        # === 日志区域 ===
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 日志滚动条
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # 配置主框架的行权重
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def _setup_hotkeys(self):
        """设置快捷键"""
        self.update_hotkey()
    
    def refresh_windows(self):
        """刷新窗口列表"""
        try:
            self.status_var.set("正在刷新窗口列表...")
            self.root.update()
            
            # 获取所有窗口，包括不可见的
            windows = self.window_capture.get_all_windows(include_invisible=True)
            
            # 过滤和排序窗口
            valid_windows = []
            for win in windows:
                try:
                    size = win.get_size()
                    # 添加窗口状态信息
                    status = ""
                    if win.is_minimized():
                        status = " [最小化]"
                    elif not win.is_visible():
                        status = " [隐藏]"
                    
                    display_name = f"{win.title}{status} ({size[0]}x{size[1]})"
                    valid_windows.append((win, display_name))
                except Exception as e:
                    self.log(f"处理窗口 {win.title} 时出错: {e}")
                    continue
            
            # 按窗口标题排序
            valid_windows.sort(key=lambda x: x[0].title.lower())
            
            # 更新下拉框
            self.windows_list = [win for win, _ in valid_windows]
            window_titles = [display_name for _, display_name in valid_windows]
            
            self.window_combo['values'] = window_titles
            
            self.log(f"已刷新窗口列表，找到 {len(valid_windows)} 个窗口")
            
            if valid_windows:
                self.status_var.set(f"找到 {len(valid_windows)} 个可用窗口")
                
                # 显示窗口类型统计
                visible_count = sum(1 for win, _ in valid_windows if win.is_visible() and not win.is_minimized())
                minimized_count = sum(1 for win, _ in valid_windows if win.is_minimized())
                hidden_count = len(valid_windows) - visible_count - minimized_count
                
                self.log(f"窗口状态: 可见 {visible_count}, 最小化 {minimized_count}, 隐藏 {hidden_count}")
            else:
                self.status_var.set("未找到可用窗口")
                self.log("未找到任何可用窗口，请检查是否有程序在运行")
                
        except Exception as e:
            error_msg = f"刷新窗口列表失败: {e}"
            self.log(error_msg)
            self.status_var.set("刷新失败")
            messagebox.showerror("错误", f"{error_msg}\n\n请尝试以管理员权限运行程序")
    
    def on_window_selected(self, event=None):
        """窗口选择事件处理"""
        selection = self.window_combo.current()
        if selection >= 0 and hasattr(self, 'windows_list'):
            self.selected_window = self.windows_list[selection]
            self.window_capture.set_target_window(self.selected_window)
            
            self.status_var.set(f"已选择窗口: {self.selected_window.title}")
            self.log(f"选择窗口: {self.selected_window.title}")
            
            # 启用捕获按钮
            self.capture_btn.configure(state="normal")
    
    def update_hotkey(self):
        """更新快捷键设置"""
        try:
            hotkey = self.capture_hotkey.get().strip()
            if hotkey:
                # 移除旧的快捷键
                self.hotkey_manager.remove_all_hotkeys()
                
                # 添加新的快捷键
                self.hotkey_manager.add_hotkey(hotkey, self.hotkey_capture)
                
                self.log(f"快捷键已设置为: {hotkey}")
                self.capture_btn.configure(text=f"立即截图 ({hotkey})")
            
        except Exception as e:
            self.log(f"设置快捷键失败: {e}")
            messagebox.showerror("错误", f"设置快捷键失败: {e}")
    
    def hotkey_capture(self):
        """快捷键触发的截图"""
        if self.selected_window:
            # 在主线程中执行截图
            self.root.after(0, self.manual_capture)
    
    def manual_capture(self):
        """手动截图"""
        if not self.selected_window:
            messagebox.showwarning("警告", "请先选择要截图的窗口")
            return
        
        try:
            self.status_var.set("正在截图...")
            self.root.update()
            
            # 检查窗口是否仍然存在
            if not self.selected_window.is_visible():
                self.log("警告: 目标窗口不可见，尝试继续截图...")
            
            # 捕获窗口
            self.log(f"开始截图窗口: {self.selected_window.title}")
            img = self.window_capture.capture_window(self.selected_window)
            
            if img is not None and img.size > 0:
                # 检查图像是否有效
                height, width = img.shape[:2]
                if height > 0 and width > 0:
                    self.log(f"截图成功，尺寸: {width}x{height}")
                    
                    # 更新预览
                    self.update_preview(img)
                    
                    # 自动保存
                    if self.auto_save.get():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshot_{timestamp}.png"
                        filepath = os.path.join(self.save_directory, filename)
                        
                        success = cv2.imwrite(filepath, img)
                        if success:
                            self.log(f"截图已保存: {filename}")
                            self.status_var.set(f"截图成功: {filename}")
                        else:
                            self.log("保存截图失败")
                            self.status_var.set("截图成功但保存失败")
                    else:
                        self.status_var.set("截图成功（未保存）")
                        self.log("截图成功（未自动保存）")
                else:
                    self.log("截图失败: 图像尺寸无效")
                    self.status_var.set("截图失败: 图像无效")
                    messagebox.showerror("错误", "截图失败：获取的图像尺寸无效")
            else:
                self.log("截图失败: 未获取到图像数据")
                self.status_var.set("截图失败")
                
                # 提供更详细的错误信息和解决建议
                error_msg = (
                    "截图失败，可能的原因：\n\n"
                    "1. 窗口被最小化或隐藏\n"
                    "2. 窗口使用了特殊的渲染方式\n"
                    "3. 需要管理员权限\n\n"
                    "建议解决方案：\n"
                    "• 确保窗口可见且未最小化\n"
                    "• 尝试以管理员权限运行程序\n"
                    "• 切换窗口到窗口化模式（非全屏）"
                )
                messagebox.showerror("截图失败", error_msg)
                
        except Exception as e:
            error_msg = f"截图过程出错: {str(e)}"
            self.log(error_msg)
            self.status_var.set("截图出错")
            
            # 提供详细的错误信息
            detailed_error = (
                f"截图过程中发生错误：\n\n"
                f"错误详情: {str(e)}\n\n"
                f"目标窗口: {self.selected_window.title if self.selected_window else '未选择'}\n"
                f"窗口句柄: {self.selected_window.hwnd if self.selected_window else 'N/A'}\n\n"
                f"请尝试：\n"
                f"• 重新选择窗口\n"
                f"• 以管理员权限运行\n"
                f"• 检查窗口是否正常显示"
            )
            messagebox.showerror("截图错误", detailed_error)
    
    def preview_window(self):
        """预览窗口"""
        if not self.selected_window:
            messagebox.showwarning("警告", "请先选择要预览的窗口")
            return
        
        try:
            img = self.window_capture.capture_window(self.selected_window)
            if img is not None:
                self.update_preview(img)
                self.log("窗口预览已更新")
            else:
                messagebox.showerror("错误", "无法预览窗口")
                
        except Exception as e:
            self.log(f"预览窗口失败: {e}")
            messagebox.showerror("错误", f"预览窗口失败: {e}")
    
    def update_preview(self, img: np.ndarray):
        """更新预览图像"""
        try:
            # 转换为RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 计算缩放比例以适应画布
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width <= 1:  # 画布还未初始化
                canvas_width = 400
                canvas_height = 200
            
            img_height, img_width = img_rgb.shape[:2]
            scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 调整图像大小
            img_resized = cv2.resize(img_rgb, (new_width, new_height))
            
            # 转换为PIL图像
            pil_img = Image.fromarray(img_resized)
            self.preview_photo = ImageTk.PhotoImage(pil_img)
            
            # 清除画布并显示图像
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.preview_photo, anchor=tk.CENTER
            )
            
        except Exception as e:
            self.log(f"更新预览失败: {e}")
    
    def browse_directory(self):
        """浏览保存目录"""
        directory = filedialog.askdirectory(initialdir=self.save_directory)
        if directory:
            self.save_directory = directory
            self.dir_var.set(directory)
            self.log(f"保存目录已更改为: {directory}")
    
    def open_save_directory(self):
        """打开保存目录"""
        try:
            os.startfile(self.save_directory)
        except Exception as e:
            self.log(f"打开目录失败: {e}")
            messagebox.showerror("错误", f"打开目录失败: {e}")
    
    def log(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # 限制日志长度
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 100:
            self.log_text.delete("1.0", "10.0")
    
    def on_closing(self):
        """窗口关闭事件"""
        try:
            # 清理快捷键
            self.hotkey_manager.remove_all_hotkeys()
            self.hotkey_manager.stop()
            
            # 停止捕获
            self.window_capture.stop_continuous_capture()
            
            self.log("程序正在退出...")
            
        except Exception as e:
            print(f"清理资源时出错: {e}")
        
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动快捷键监听
        self.hotkey_manager.start()
        
        self.log("截图器已启动")
        self.log(f"保存目录: {self.save_directory}")
        
        # 运行主循环
        self.root.mainloop()


# === 便捷函数 ===

def launch_capture_gui():
    """启动截图器GUI"""
    try:
        app = CaptureGUI()
        app.run()
    except Exception as e:
        print(f"启动截图器失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    launch_capture_gui()
