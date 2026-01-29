"""
窗口获取功能测试

直接运行此文件即可测试窗口获取功能，打印出所有获取到的窗口
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.window_capture import WindowCapture


def main():
    """主程序 - 完全测试窗口可见性逻辑"""
    print("窗口获取功能完整测试")
    print("=" * 60)
    
    try:
        capture = WindowCapture()
        
        # 先获取所有窗口（包括隐藏的）
        print("1. 获取所有窗口（包括隐藏）...")
        all_windows = capture.get_all_windows(include_invisible=True)
        print(f"   总窗口数: {len(all_windows)}")
        
        # 再获取可见窗口
        print("\n2. 获取可见窗口...")
        visible_windows = capture.get_all_windows(include_invisible=False)
        print(f"   可见窗口数: {len(visible_windows)}")
        
        # 详细测试每个窗口的状态
        print("\n3. 详细分析所有窗口状态:")
        print("-" * 60)
        
        truly_visible = []
        
        for i, window in enumerate(all_windows, 1):
            try:
                size = window.get_size()
                is_visible = window.is_visible()
                is_minimized = window.is_minimized()
                
                # 判断是否应该被认为是"可见"
                should_be_visible = is_visible and not is_minimized
                
                if should_be_visible:
                    truly_visible.append(window)
                
                status = []
                if is_visible:
                    status.append("可见")
                else:
                    status.append("隐藏")
                    
                if is_minimized:
                    status.append("最小化")
                
                status_str = "+".join(status)
                should_show = "✅" if should_be_visible else "❌"
                
                print(f"{i:3d}. {should_show} {window.title}")
                print(f"     状态: {status_str}")
                print(f"     尺寸: {size[0]}x{size[1]}")
                print(f"     类名: {window.class_name}")
                print()
                
            except Exception as e:
                print(f"{i:3d}. ❌ {window.title} [检查失败: {e}]")
                print()
        
        print("=" * 60)
        print("测试结果汇总:")
        print(f"  总窗口数: {len(all_windows)}")
        print(f"  get_all_windows(False)返回: {len(visible_windows)} 个")
        print(f"  手动筛选真正可见: {len(truly_visible)} 个")
        
        if len(visible_windows) != len(truly_visible):
            print(f"⚠️  过滤逻辑有问题！应该返回 {len(truly_visible)} 个，实际返回 {len(visible_windows)} 个")
        else:
            print("✅ 过滤逻辑正确！")
        
        print("\n4. 最终的可见窗口列表:")
        print("-" * 60)
        for i, window in enumerate(truly_visible, 1):
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
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    main()