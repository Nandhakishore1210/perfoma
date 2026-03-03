import os
import subprocess
import sys
import shutil

def build():
    print("Starting Portable Bundle Process...")
    
    # Paths
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root_dir, "dist")
    bundle_dir = os.path.join(dist_dir, "Perfoma_Portable")
    frontend_dist = os.path.join(root_dir, "frontend", "dist")
    
    if not os.path.exists(frontend_dist):
        print("Error: Frontend dist not found. Please build the frontend first.")
        return

    # Clean previous builds
    for folder in [dist_dir, os.path.join(root_dir, "build")]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not clean {folder}. Error: {e}")

    # PyInstaller command
    # Exhaustive collection to ensure every module (PDF, Excel, DB) is included
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean", # FORCE CLEAN CACHE
        "--onedir", # Using folder mode for maximum stability
        "--name", "PerfomaApp",
        "--contents-directory", "internal",
        # Add frontend files
        f"--add-data={frontend_dist};frontend/dist",
        # Add backend app directory
        f"--add-data={os.path.join(root_dir, 'backend', 'app')};app",
        
        # EVERY package from requirements.txt collected fully
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_settings",
        "--collect-all", "pandas",
        "--collect-all", "sqlalchemy",
        "--collect-all", "pdfplumber", # Specifically requested fix
        "--collect-all", "xlsxwriter",
        "--collect-all", "reportlab",
        "--collect-all", "openpyxl",
        "--collect-all", "passlib",
        "--collect-all", "jose",
        
        # Hidden imports for stability
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi.middleware.cors",
        "--hidden-import=sqlalchemy.sql.default_comparator",
        
        # Exclude only the heaviest non-functional bloat
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "IPython",
        "--exclude-module", "pytest",
        
        # Entry point
        "run_app.py"
    ]

    print(f"Running PyInstaller...")
    result = subprocess.run(cmd, check=False)
    
    if result.returncode == 0:
        # Move internal dist/PerfomaApp to bundle_dir
        app_output = os.path.join(dist_dir, "PerfomaApp")
        if os.path.exists(bundle_dir):
            shutil.rmtree(bundle_dir)
        os.rename(app_output, bundle_dir)
        
        # Create a simple .bat launcher at the root
        bat_content = "@echo off\necho Starting Perfoma System...\necho Please wait, this may take a few seconds...\ncd /d \"%~dp0\"\nstart PerfomaApp.exe\nexit"
        with open(os.path.join(bundle_dir, "Start-Perfoma.bat"), "w") as f:
            f.write(bat_content)

        print("\nSUCCESS! Your Portable Folder is ready.")
        print(f"Location: {bundle_dir}")
        print("To share it: Zip the 'Perfoma_Portable' folder and send it.")
    else:
        print("\nBuild failed. Check the errors above.")

if __name__ == "__main__":
    build()
