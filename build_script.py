import os
import PyInstaller.__main__
import shutil
import platform
import sys
import glob
import site
import pkg_resources

# Configuration
APP_NAME = "DatabaseManager"
SCRIPT_PATH = "src/main.py"
DIST_PATH = "dist"
BUILD_PATH = "build"

# Path to magic files
MAGIC_DIR = r"C:\Users\user\AppData\Local\Programs\Python\Python313\Lib\site-packages\magic\libmagic"
LIBMAGIC_DLL = os.path.join(MAGIC_DIR, "libmagic.dll")
MAGIC_MGC = os.path.join(MAGIC_DIR, "magic.mgc")

def main():
    # Clean previous builds
    if os.path.exists(DIST_PATH):
        shutil.rmtree(DIST_PATH)
    if os.path.exists(BUILD_PATH):
        shutil.rmtree(BUILD_PATH)
    
    # Verify magic files exist
    missing_files = []
    if not os.path.exists(LIBMAGIC_DLL):
        missing_files.append(LIBMAGIC_DLL)
    if not os.path.exists(MAGIC_MGC):
        missing_files.append(MAGIC_MGC)
    
    if missing_files:
        print("ERROR: Missing required magic files:")
        for file in missing_files:
            print(f"  - {file}")
        print("Build cannot continue.")
        return
    
    print("Found required magic files:")
    print(f"  - libmagic.dll: {os.path.exists(LIBMAGIC_DLL)}")
    print(f"  - magic.mgc: {os.path.exists(MAGIC_MGC)}")
    
    # Prepare PyInstaller command
    cmd = [
        SCRIPT_PATH,
        f"--name={APP_NAME}",
        "--onefile",
        "--windowed",
        f"--distpath={DIST_PATH}",
        f"--workpath={BUILD_PATH}",
        
        # Add core application files
        "--add-data=src/core;core",
        "--add-data=src/gui;gui",
        "--add-data=src/plugins;plugins",  
        "--add-data=src/file_processor.py;.",
        "--add-data=src/core/database.py;.",
        "--add-data=src/config;config",
        "--add-data=src/config/mongodb_config.json;config",
        
        # Add magic files
        f"--add-binary={LIBMAGIC_DLL};.",
        f"--add-data={MAGIC_MGC};.",
        
        # Critical hidden imports
        "--hidden-import=core.transformation",
        "--hidden-import=jsonschema",
        "--hidden-import=PyPDF2",
        "--hidden-import=docx",
        "--hidden-import=docx.oxml",
        "--hidden-import=docx.opc",
        "--hidden-import=docx.oxml.ns",
        "--hidden-import=docx.oxml.shape",
        "--hidden-import=docx.oxml.text",
        "--hidden-import=magic",
        "--hidden-import=requests",
        "--hidden-import=pandas",
        "--hidden-import=sqlalchemy",
        "--hidden-import=pymysql",
        "--hidden-import=customtkinter",
        "--hidden-import=pymongo",
        "--hidden-import=gridfs",
        "--hidden-import=bson",

        
        # Collect package data
        "--collect-data=magic",
        "--collect-data=PyPDF2",
        "--collect-data=python_docx",
        "--collect-data=pymongo",
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(cmd)
    
    # Manual copy of critical files
    shutil.copy(LIBMAGIC_DLL, DIST_PATH)
    shutil.copy(MAGIC_MGC, DIST_PATH)
    shutil.copytree("src/config", os.path.join(DIST_PATH, "config"), dirs_exist_ok=True)
    
    print(f"\nBuild complete! Executable is in: {os.path.abspath(DIST_PATH)}")

if __name__ == "__main__":
    main()