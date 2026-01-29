"""
GameSceneClassifier 截图工具主程序

专用于游戏场景数据收集的截图工具
提供GUI界面和命令行两种使用方式
"""

import sys
import os
import argparse
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from utils import (
        launch_screenshot_gui,
        interactive_screenshot_setup,
        create_screenshot_tool,
        quick_screenshot,
        get_window_list,
        test_window_detection
    )
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("\n请确保已安装必要的依赖:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def show_help():
    """显示帮助信息"""
    print("=== GameSceneClassifier 截图工具 ===")
    print()
    print("用法:")
    print("  python screenshot_tool.py [选项]")
    print()
    print("选项:")
    print("  -h, --help          显示此帮助信息")
    print("  -g, --gui           启动GUI界面 (默认)")
    print("  -i, --interactive   启动交互式命令行模式")
    print("  -l, --list          列出所有可用窗口")
    print("  -t, --test          测试窗口获取功能")
    print("  -w, --window TITLE  指定窗口标题进行快速设置")
    print("  -k, --hotkey KEY    设置快捷键 (默认: F9)")
    print("  -d, --dir PATH      设置保存目录")
    print()
    print("示例:")
    print("  python screenshot_tool.py                    # 启动GUI")
    print("  python screenshot_tool.py -i                 # 交互模式")
    print("  python screenshot_tool.py -l                 # 列出窗口")
    print("  python screenshot_tool.py -t                 # 测试窗口获取")
    print("  python screenshot_tool.py -w \"游戏窗口\"      # 快速设置")
    print("  python screenshot_tool.py -w \"游戏\" -k F10   # 自定义快捷键")


def list_windows():
    """列出所有可用窗口"""
    # 直接调用utils中的窗口检测函数
    test_window_detection()


def quick_setup(window_title: str, hotkey: str = "F9", save_dir: str = None):
    """快速设置截图工具"""
    print(f"=== 快速设置截图工具 ===")
    print(f"目标窗口: {window_title}")
    print(f"快捷键: {hotkey}")
    print(f"保存目录: {save_dir or '默认(./screenshots)'}")
    print()
    
    try:
        # 创建截图工具
        tool = create_screenshot_tool(
            save_directory=save_dir,
            default_hotkey=hotkey
        )
        
        # 设置目标窗口
        if tool.set_target_window_by_title(window_title):
            print(f"✅ 截图工具已就绪!")
            print(f"按 {hotkey} 开始截图")
            print("按 Ctrl+C 退出")
            print()
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在退出...")
                tool.cleanup()
                
        else:
            print(f"❌ 未找到窗口: {window_title}")
            print("\n可用窗口:")
            windows = tool.get_available_windows()
            for i, window in enumerate(windows[:10], 1):
                print(f"  {i}. {window.title}")
            
    except Exception as e:
        print(f"设置失败: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="GameSceneClassifier 截图工具",
        add_help=False  # 使用自定义帮助
    )
    
    parser.add_argument('-h', '--help', action='store_true', help='显示帮助信息')
    parser.add_argument('-g', '--gui', action='store_true', help='启动GUI界面')
    parser.add_argument('-i', '--interactive', action='store_true', help='交互式模式')
    parser.add_argument('-l', '--list', action='store_true', help='列出所有窗口')
    parser.add_argument('-t', '--test', action='store_true', help='测试窗口获取功能')
    parser.add_argument('-w', '--window', type=str, help='指定窗口标题')
    parser.add_argument('-k', '--hotkey', type=str, default='F9', help='设置快捷键')
    parser.add_argument('-d', '--dir', type=str, help='设置保存目录')
    
    args = parser.parse_args()
    
    # 显示帮助
    if args.help:
        show_help()
        return
    
    # 列出窗口
    if args.list:
        list_windows()
        return
    
    # 测试窗口获取功能
    if args.test:
        test_window_detection()
        return
    
    # 快速设置模式
    if args.window:
        quick_setup(args.window, args.hotkey, args.dir)
        return
    
    # 交互式模式
    if args.interactive:
        print("正在启动交互模式...")
        tool = interactive_screenshot_setup()
        if tool:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在退出...")
                tool.cleanup()
        return
    
    # 默认启动GUI
    print("正在启动GUI界面...")
    try:
        launch_screenshot_gui()
    except Exception as e:
        print(f"启动GUI失败: {e}")
        print("\n尝试交互模式...")
        tool = interactive_screenshot_setup()
        if tool:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在退出...")
                tool.cleanup()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消操作")
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()
