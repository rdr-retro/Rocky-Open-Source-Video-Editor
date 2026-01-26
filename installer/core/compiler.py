import os
import subprocess
import urllib.request
import zipfile
import shutil
import tempfile

class EnvironmentManager:
    @staticmethod
    def setup_app(install_dir, progress_callback=None):
        """Full setup using embedded Python, portable MinGW, and FFmpeg."""
        from core.system import SystemManager
        
        # 1. Setup Embedded Python
        py_dir = SystemManager.setup_embedded_python(install_dir, progress_callback)
        python_exe = os.path.join(py_dir, "python.exe")
        
        # 2. Pip Dependencies
        if progress_callback: progress_callback("Instalando dependencias de Python...")
        # Add pip to path temporarily or call it via module
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "pyinstaller"], check=True, cwd=install_dir)
        if os.path.exists(os.path.join(install_dir, "requirements.txt")):
            subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=True, cwd=install_dir)
        
        # 3. Externals (FFmpeg & MinGW)
        EnvironmentManager._setup_ffmpeg(install_dir, progress_callback)
        EnvironmentManager._setup_mingw(install_dir, progress_callback)
        
        # 4. Compile C++ Core
        if progress_callback: progress_callback("Compilando Rocky Core (C++)...")
        env = os.environ.copy()
        # Add MinGW to PATH for this process
        mingw_bin = os.path.abspath(os.path.join(install_dir, "external", "mingw", "bin"))
        env["PATH"] = f"{mingw_bin};" + env["PATH"]
        
        if os.path.exists(os.path.join(install_dir, "setup.py")):
            subprocess.run([python_exe, "setup.py", "build_ext", "--inplace", "--compiler=mingw32"], check=True, cwd=install_dir, env=env)
        
        return True

    @staticmethod
    def _setup_ffmpeg(install_dir, progress_callback):
        ext_dir = os.path.join(install_dir, "external")
        ff_dir = os.path.join(ext_dir, "ffmpeg")
        if os.path.exists(ff_dir): return
        
        if progress_callback: progress_callback("Descargando FFmpeg...")
        os.makedirs(ext_dir, exist_ok=True)
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
        # ... (Implementation of download/extract from downloader.py logic)
        from core.downloader import RepositoryManager
        tmp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")
        urllib.request.urlretrieve(url, tmp_zip)
        
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(ext_dir)
            extracted = [d for d in os.listdir(ext_dir) if d.startswith("ffmpeg-")][0]
            shutil.move(os.path.join(ext_dir, extracted), ff_dir)

    @staticmethod
    def _setup_mingw(install_dir, progress_callback):
        ext_dir = os.path.join(install_dir, "external")
        mw_dir = os.path.join(ext_dir, "mingw")
        if os.path.exists(mw_dir): return
        
        if progress_callback: progress_callback("Instalando MinGW Portable (Compilador)...")
        url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/14.2.0posix-18.1.8-12.0.0-msvcrt-r1/winlibs-x86_64-posix-seh-gcc-14.2.0-mingw-w64msvcrt-12.0.0-r1.zip"
        tmp_zip = os.path.join(tempfile.gettempdir(), "mingw.zip")
        urllib.request.urlretrieve(url, tmp_zip)
        
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(ext_dir)
            extracted = [d for d in os.listdir(ext_dir) if d.startswith("mingw64")][0]
            shutil.move(os.path.join(ext_dir, extracted), mw_dir)

    @staticmethod
    def generate_app_exe(install_dir, progress_callback=None):
        """Creates a standalone .exe for the application using PyInstaller."""
        if progress_callback: progress_callback("Generando RockyEditor.exe final...")
        py_exe = os.path.join(install_dir, "python_env", "python.exe")
        
        # Minimal launcher script
        launcher_py = os.path.join(install_dir, "_launcher.py")
        with open(launcher_py, "w") as f:
            f.write("import os, sys\n"
                    "curr = os.path.dirname(os.path.abspath(__file__))\n"
                    "os.environ['PATH'] = os.path.join(curr, 'external', 'ffmpeg', 'bin') + ';' + os.environ['PATH']\n"
                    "import main\n"
                    "if __name__ == '__main__':\n"
                    "    main.main()\n")
        
        # Build EXE using PyInstaller inside the embedded environment
        subprocess.run([py_exe, "-m", "PyInstaller", "--onefile", "--noconsole", "--name", "RockyEditor", "_launcher.py"], check=True, cwd=install_dir)
        
        # Final cleanup
        if os.path.exists(launcher_py): os.remove(launcher_py)
        return True

    @staticmethod
    def create_desktop_shortcut(install_dir):
        """Creates a .lnk on the Desktop using PowerShell to avoid dependencies."""
        exe_path = os.path.join(install_dir, "dist", "RockyEditor.exe")
        if not os.path.exists(exe_path):
            # Fallback if EXE wasn't built yet or failed
            return
            
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, "Rocky Editor.lnk")
        
        ps_cmd = (
            f"$s=(New-Object -Com Object WScript.Shell).CreateShortcut('{shortcut_path}');"
            f"$s.TargetPath='{exe_path}';"
            f"$s.WorkingDirectory='{install_dir}';"
            f"$s.Save()"
        )
        
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
