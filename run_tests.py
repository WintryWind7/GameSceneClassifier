"""
GameSceneClassifier 测试运行器

运行项目的各种测试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """主函数"""
    print("=== GameSceneClassifier 测试运行器 ===")
    print()
    
    try:
        from tests.test_window_capture import run_all_tests, interactive_window_test
        
        print("可用的测试:")
        print("1. 窗口捕获功能测试 (自动)")
        print("2. 窗口捕获功能测试 (交互式)")
        print("3. 运行所有测试")
        print()
        
        choice = input("请选择测试类型 (1-3, 默认3): ").strip() or "3"
        
        if choice == "1":
            print("\n正在运行自动测试...")
            run_all_tests()
            
        elif choice == "2":
            print("\n正在运行交互式测试...")
            interactive_window_test()
            
        elif choice == "3":
            print("\n正在运行所有测试...")
            run_all_tests()
            
            # 询问是否继续交互测试
            try:
                cont = input("\n是否继续交互式测试? (y/N): ").strip().lower()
                if cont == 'y':
                    interactive_window_test()
            except KeyboardInterrupt:
                print("\n测试结束")
        
        else:
            print("无效选择，运行默认测试...")
            run_all_tests()
    
    except ImportError as e:
        print(f"导入测试模块失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
    
    except KeyboardInterrupt:
        print("\n用户取消测试")
    
    except Exception as e:
        print(f"测试运行出错: {e}")


if __name__ == "__main__":
    main()
