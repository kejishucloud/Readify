#!/usr/bin/env python3
"""
优化书籍渲染器安装脚本
安装所需的依赖包和配置
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """运行命令并处理错误"""
    print(f"\n正在{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description}失败: {e.stderr}")
        return False

def install_python_packages():
    """安装Python依赖包"""
    packages = [
        "PyMuPDF==1.23.8",
        "lxml==4.9.3", 
        "markdown-extensions==0.1.3",
        "opencv-python==4.8.1.78",
        "cchardet==2.1.7"
    ]
    
    print("正在安装Python依赖包...")
    for package in packages:
        if not run_command(f"pip install {package}", f"安装 {package}"):
            print(f"警告: {package} 安装失败，可能影响某些功能")
    
    return True

def install_calibre():
    """安装Calibre（用于MOBI/AZW3转换）"""
    system = platform.system().lower()
    
    print("\n正在检查Calibre安装...")
    
    # 检查是否已安装
    try:
        subprocess.run(["ebook-convert", "--version"], capture_output=True, check=True)
        print("✓ Calibre已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("Calibre未安装，正在尝试安装...")
    
    if system == "windows":
        print("请手动下载并安装Calibre:")
        print("https://calibre-ebook.com/download_windows")
        print("安装后请将Calibre添加到系统PATH中")
        
    elif system == "darwin":  # macOS
        if run_command("brew --version", "检查Homebrew"):
            run_command("brew install --cask calibre", "通过Homebrew安装Calibre")
        else:
            print("请手动下载并安装Calibre:")
            print("https://calibre-ebook.com/download_osx")
            
    elif system == "linux":
        # 尝试不同的包管理器
        if run_command("apt --version", "检查apt"):
            run_command("sudo apt update && sudo apt install -y calibre", "通过apt安装Calibre")
        elif run_command("yum --version", "检查yum"):
            run_command("sudo yum install -y calibre", "通过yum安装Calibre")
        elif run_command("dnf --version", "检查dnf"):
            run_command("sudo dnf install -y calibre", "通过dnf安装Calibre")
        else:
            print("请手动安装Calibre:")
            print("https://calibre-ebook.com/download_linux")
    
    return True

def create_conda_environment():
    """创建conda环境（如果使用conda）"""
    try:
        subprocess.run(["conda", "--version"], capture_output=True, check=True)
        print("\n检测到conda环境")
        
        # 检查是否在conda环境中
        conda_env = os.environ.get('CONDA_DEFAULT_ENV')
        if conda_env and conda_env != 'base':
            print(f"当前在conda环境: {conda_env}")
            
            # 安装conda-forge包
            conda_packages = [
                "lxml",
                "opencv", 
                "chardet"
            ]
            
            for package in conda_packages:
                run_command(f"conda install -c conda-forge {package} -y", f"安装conda包 {package}")
                
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("未检测到conda环境，跳过conda包安装")
        return True

def check_system_requirements():
    """检查系统要求"""
    print("正在检查系统要求...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"✗ Python版本过低: {python_version.major}.{python_version.minor}")
        print("需要Python 3.8或更高版本")
        return False
    else:
        print(f"✓ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
        print("✓ pip可用")
    except subprocess.CalledProcessError:
        print("✗ pip不可用")
        return False
    
    return True

def update_django_settings():
    """更新Django设置"""
    print("\n正在检查Django设置...")
    
    settings_file = "readify/settings.py"
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否需要添加新的设置
        additions = []
        
        if 'OPTIMIZED_RENDERER_SETTINGS' not in content:
            additions.append("""
# 优化渲染器设置
OPTIMIZED_RENDERER_SETTINGS = {
    'ENABLE_MUPDF': True,
    'ENABLE_CALIBRE_CONVERSION': True,
    'TEMP_DIR': os.path.join(BASE_DIR, 'temp', 'renderer'),
    'MAX_FILE_SIZE': 100 * 1024 * 1024,  # 100MB
    'CACHE_RENDERED_CONTENT': True,
    'CACHE_TIMEOUT': 3600,  # 1小时
}
""")
        
        if additions:
            with open(settings_file, 'a', encoding='utf-8') as f:
                f.write('\n'.join(additions))
            print("✓ Django设置已更新")
        else:
            print("✓ Django设置已是最新")
    else:
        print("✗ 未找到Django设置文件")
        return False
    
    return True

def create_temp_directories():
    """创建临时目录"""
    print("\n正在创建临时目录...")
    
    temp_dirs = [
        "temp/renderer",
        "temp/epub_extract", 
        "temp/pdf_cache",
        "temp/mobi_convert"
    ]
    
    for dir_path in temp_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")
    
    return True

def run_django_migrations():
    """运行Django迁移"""
    print("\n正在运行Django迁移...")
    
    if run_command("python manage.py makemigrations", "生成迁移文件"):
        run_command("python manage.py migrate", "应用迁移")
    
    return True

def main():
    """主安装流程"""
    print("=" * 60)
    print("优化书籍渲染器安装程序")
    print("=" * 60)
    
    # 检查系统要求
    if not check_system_requirements():
        print("\n系统要求检查失败，请解决上述问题后重试")
        sys.exit(1)
    
    # 创建conda环境（如果适用）
    create_conda_environment()
    
    # 安装Python包
    install_python_packages()
    
    # 安装Calibre
    install_calibre()
    
    # 更新Django设置
    update_django_settings()
    
    # 创建临时目录
    create_temp_directories()
    
    # 运行Django迁移
    run_django_migrations()
    
    print("\n" + "=" * 60)
    print("安装完成！")
    print("=" * 60)
    print("\n支持的格式和渲染引擎:")
    print("• EPUB → WebKit/Chromium (epub.js)")
    print("• PDF → MuPDF/Poppler")
    print("• MOBI/AZW3 → EPUB转换 (需要Calibre)")
    print("• FB2 → XSLT转XHTML")
    print("• TXT/Markdown/HTML → 浏览器渲染")
    
    print("\n使用方法:")
    print("1. 上传书籍文件")
    print("2. 在书籍详情页点击'优化阅读器'按钮")
    print("3. 享受针对不同格式优化的阅读体验")
    
    print("\n注意事项:")
    print("• 首次渲染可能需要较长时间")
    print("• 大文件建议使用分页模式")
    print("• MOBI/AZW3格式需要安装Calibre")
    
    print("\n如有问题，请检查日志文件或联系技术支持")

if __name__ == "__main__":
    main() 