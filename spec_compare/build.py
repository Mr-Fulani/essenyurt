"""
Build script for Specification Comparison Tool
Скрипт сборки приложения сравнения спецификаций
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def clean_build():
    """Clean build directories"""
    dirs_to_remove = ['build', 'dist', '__pycache__', '.pytest_cache']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/...")
            shutil.rmtree(dir_name)
    
    # Remove .pyc files
    for pyc_file in Path('.').rglob('*.pyc'):
        pyc_file.unlink()
    
    # Remove .spec files
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
    
    print("Clean complete!")


def build_windows():
    """Build Windows executable"""
    print("\n" + "=" * 60)
    print("Building Windows executable (.exe)")
    print("=" * 60)
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'SpecCompare',
        '--icon', 'NONE',
        '--add-data', 'src/*.py;src',
        '--hidden-import', 'sklearn.utils._typedefs',
        '--hidden-import', 'sklearn.neighbors._partition_nodes',
        'src/main.py'
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ Windows build complete!")
    print("Executable: dist/SpecCompare.exe")


def build_macos():
    """Build macOS application"""
    print("\n" + "=" * 60)
    print("Building macOS application (.app)")
    print("=" * 60)
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'SpecCompare',
        '--icon', 'NONE',
        '--add-data', 'src/*.py:src',
        '--hidden-import', 'sklearn.utils._typedefs',
        '--hidden-import', 'sklearn.neighbors._partition_nodes',
        'src/main.py'
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ macOS build complete!")
    print("Application: dist/SpecCompare")


def build_current_platform():
    """Build for current platform"""
    print("\n" + "=" * 60)
    print("Building for current platform")
    print("=" * 60)
    
    platform = sys.platform
    
    if platform == 'win32':
        build_windows()
    elif platform == 'darwin':
        build_macos()
    else:
        print(f"Platform {platform} not supported for automated build")
        print("Please use: pyinstaller --onefile --windowed src/main.py")


def create_distribution():
    """Create distribution package"""
    print("\n" + "=" * 60)
    print("Creating distribution package")
    print("=" * 60)
    
    dist_dir = Path('dist')
    package_dir = Path('package')
    
    # Create package directory
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    # Copy executable
    platform = sys.platform
    if platform == 'win32':
        exe_name = 'SpecCompare.exe'
    else:
        exe_name = 'SpecCompare'
    
    src_exe = dist_dir / exe_name
    if src_exe.exists():
        shutil.copy(src_exe, package_dir / exe_name)
    
    # Copy test files
    test_dest = package_dir / 'test_files'
    test_dest.mkdir()
    for test_file in Path('test_files').glob('*.xlsx'):
        shutil.copy(test_file, test_dest)
    
    # Copy documentation
    shutil.copy('README.md', package_dir)
    shutil.copy('requirements.txt', package_dir)
    
    print(f"\n✅ Package created: {package_dir}/")


def main():
    """Main build function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build SpecCompare application')
    parser.add_argument('--clean', action='store_true', help='Clean build directories')
    parser.add_argument('--windows', action='store_true', help='Build Windows executable')
    parser.add_argument('--macos', action='store_true', help='Build macOS application')
    parser.add_argument('--package', action='store_true', help='Create distribution package')
    parser.add_argument('--all', action='store_true', help='Build and package for current platform')
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    if args.clean:
        clean_build()
        return
    
    if args.windows:
        build_windows()
    elif args.macos:
        build_macos()
    elif args.all:
        clean_build()
        build_current_platform()
        if args.package:
            create_distribution()
    else:
        # Default: build for current platform
        clean_build()
        build_current_platform()


if __name__ == '__main__':
    main()
