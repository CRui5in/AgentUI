#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查脚本
检查项目运行所需的依赖和环境配置
"""

import sys
import subprocess
import importlib
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("检查 Python 版本...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} - 版本符合要求")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} - 需要 Python 3.9+")
        return False


def check_poetry():
    """检查 Poetry 是否安装"""
    print("\n检查 Poetry...")
    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ {result.stdout.strip()}")
            return True
        else:
            print("✗ Poetry 未安装或无法运行")
            return False
    except FileNotFoundError:
        print("✗ Poetry 未安装")
        print("请安装 Poetry: https://python-poetry.org/docs/#installation")
        return False


def check_node():
    """检查 Node.js 是否安装"""
    print("\n检查 Node.js...")
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ Node.js {version}")
            return True
        else:
            print("✗ Node.js 未安装或无法运行")
            return False
    except FileNotFoundError:
        print("✗ Node.js 未安装")
        print("请安装 Node.js: https://nodejs.org/")
        return False


def check_npm():
    """检查 npm 是否安装"""
    print("\n检查 npm...")
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ npm {version}")
            return True
        else:
            print("✗ npm 未安装或无法运行")
            return False
    except FileNotFoundError:
        print("✗ npm 未安装")
        return False


def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")
    required_dirs = [
        "backend",
        "frontend", 
        "agent_core",
        "tool_services",
        "desktop"
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✓ {dir_name}/ 目录存在")
        else:
            print(f"✗ {dir_name}/ 目录不存在")
            all_exist = False
    
    return all_exist


def check_config_files():
    """检查配置文件"""
    print("\n检查配置文件...")
    config_files = [
        "backend/pyproject.toml",
        "agent_core/pyproject.toml",
        "tool_services/ppt_generator_service/pyproject.toml",
        "tool_services/chart_generator_service/pyproject.toml",
        "frontend/package.json",
        "desktop/package.json"
    ]
    
    all_exist = True
    for file_path in config_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} 存在")
        else:
            print(f"✗ {file_path} 不存在")
            all_exist = False
    
    return all_exist


def main():
    """主函数"""
    print("=" * 50)
    print("多功能 AI 应用环境检查")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_poetry(),
        check_node(),
        check_npm(),
        check_project_structure(),
        check_config_files()
    ]
    
    print("\n" + "=" * 50)
    print("检查结果汇总")
    print("=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✓ 所有检查通过 ({passed}/{total})")
        print("\n环境配置正确，可以运行项目！")
        print("使用以下命令启动开发环境:")
        print("  Windows: start_dev.bat")
        print("  Linux/Mac: ./start_dev.sh")
    else:
        print(f"✗ 部分检查失败 ({passed}/{total})")
        print("\n请修复上述问题后重新运行检查")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 