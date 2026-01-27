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
        if progress_callback: progress_callback("Instalando dependencias necesarias...")
        # Add pip to path temporarily or call it via module
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "pyinstaller"], check=True, cwd=install_dir)
        if os.path.exists(os.path.join(install_dir, "requirements.txt")):
            subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=True, cwd=install_dir)
        
        # 3. Externals (FFmpeg & MinGW)
        EnvironmentManager._setup_ffmpeg(install_dir, progress_callback)
        EnvironmentManager._setup_mingw(install_dir, progress_callback)
        
        # 4. Compile C++ Core
        if progress_callback: progress_callback("Compilando Rocky Core (esto puede tardar unos minutos)...")
        env = os.environ.copy()
        # Add MinGW to PATH for this process
        mingw_bin = os.path.abspath(os.path.join(install_dir, "external", "mingw", "bin"))
        env["PATH"] = f"{mingw_bin};" + env["PATH"]
        
        # 4. Compile Plugins (OFX)
        EnvironmentManager._compile_plugins(install_dir, env, progress_callback)
        
        # 5. Compile Rocky Core C++
        if os.path.exists(os.path.join(install_dir, "setup.py")):
            try:
                # Use --compiler=mingw32 to force MinGW
                result = subprocess.run(
                    [python_exe, "setup.py", "build_ext", "--inplace", "--compiler=mingw32"], 
                    check=True, 
                    cwd=install_dir, 
                    env=env,
                    capture_output=True,
                    text=True
                )
                EnvironmentManager.log_to_file(install_dir, "Compilation output:\n" + result.stdout)
            except subprocess.CalledProcessError as e:
                # Capture and log the error output
                error_msg = f"Compilation failed with exit code {e.returncode}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
                EnvironmentManager.log_to_file(install_dir, error_msg)
                raise Exception(f"Error de compilación C++:\n{e.stderr}")
        
        return True

    @staticmethod
    def log_to_file(install_dir, message):
        log_path = os.path.join(install_dir, "install_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    @staticmethod
    def _setup_ffmpeg(install_dir, progress_callback):
        ext_dir = os.path.join(install_dir, "external")
        ff_dir = os.path.join(ext_dir, "ffmpeg")
        if os.path.exists(ff_dir): return
        
        if progress_callback: progress_callback("Instalando librerías de video...")
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
        
        if progress_callback: progress_callback("Configurando compilador...")
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
        if progress_callback: progress_callback("Iniciando generación de binarios...")
        py_exe = os.path.join(install_dir, "python_env", "python.exe")
        
        # Verify integrity like run.ps1 does for dev mode
        EnvironmentManager._verify_dependencies(py_exe, install_dir, progress_callback)
        
        if progress_callback: progress_callback("Generando RockyEditor.exe final...")
        
        # Minimal launcher script
        launcher_py = os.path.join(install_dir, "_launcher.py")
        with open(launcher_py, "w") as f:
            f.write("import os, sys\n"
                    "# Force PyInstaller to bundle whisper and torch\n"
                    "import torch\n"
                    "import whisper\n"
                    "import faster_whisper\n"
                    "def get_base_path():\n"
                    "    if getattr(sys, 'frozen', False):\n"
                    "        return os.path.dirname(sys.executable)\n"
                    "    return os.path.dirname(os.path.abspath(__file__))\n"
                    "base = get_base_path()\n"
                    "if hasattr(os, 'add_dll_directory'):\n"
                    "    for d in ['external/ffmpeg/bin', 'external/mingw/bin']:\n"
                    "        full = os.path.join(base, d)\n"
                    "        if os.path.exists(full): os.add_dll_directory(full)\n"
                    "os.environ['PATH'] = os.path.join(base, 'external', 'ffmpeg', 'bin') + ';' + os.environ['PATH']\n"
                    "sys.path.append(base)\n"
                    "from src.ui.rocky_ui import main\n"
                    "if __name__ == '__main__':\n"
                    "    main()\n")
        
        # Build EXE using PyInstaller inside the embedded environment
        # --collect-all is the robust way to bundle heavy libs like whisper/torch/moviepy
        subprocess.run([
            py_exe, "-m", "PyInstaller", 
            "--onefile", "--noconsole", "--distpath", ".", 
            "--add-data", "src/ui/assets;src/ui/assets", 
            "--collect-all", "torch",
            "--collect-all", "whisper",
            "--collect-all", "faster_whisper",
            "--collect-all", "moviepy",
            "--name", "RockyEditor", "_launcher.py"
        ], check=True, cwd=install_dir)
        
        # Final cleanup
        if os.path.exists(launcher_py): os.remove(launcher_py)
        # Remove build artifacts
        shutil.rmtree(os.path.join(install_dir, "build"), ignore_errors=True)
        spec_file = os.path.join(install_dir, "RockyEditor.spec")
        if os.path.exists(spec_file): os.remove(spec_file)
        
        return True

    @staticmethod
    def _verify_dependencies(py_exe, install_dir, progress_callback):
        """Verifies that all heavy dependencies are present in the environment before building."""
        deps = ["torch", "whisper", "faster_whisper", "moviepy", "PYSide6"]
        for dep in deps:
            try:
                if progress_callback: progress_callback(f"Verificando {dep}...")
                subprocess.run([py_exe, "-c", f"import {dep.lower()}"], check=True, capture_output=True, cwd=install_dir)
            except subprocess.CalledProcessError:
                if progress_callback: progress_callback(f"ERROR: Falta {dep}. Reintentando instalación...")
                subprocess.run([py_exe, "-m", "pip", "install", dep.lower()], check=True, cwd=install_dir)

    @staticmethod
    def create_desktop_shortcut(install_dir):
        """Creates a .lnk on the Desktop using PowerShell with robust user detection."""
        exe_path = os.path.join(install_dir, "RockyEditor.exe")
        if not os.path.exists(exe_path):
            return
            
        # PowerShell script to create shortcut using [Environment]::GetFolderPath('Desktop')
        # This is more reliable for the current user than registry hacking
        ps_cmd = (
            "$desktop = [System.Environment]::GetFolderPath('Desktop');"
            "$wsh = New-Object -ComObject WScript.Shell;"
            f"$lnk = $wsh.CreateShortcut(\"$desktop\\Rocky Editor.lnk\");"
            f"$lnk.TargetPath = '{exe_path}';"
            f"$lnk.WorkingDirectory = '{install_dir}';"
            f"$lnk.Save();"
        )
        
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)

    @staticmethod
    def _compile_plugins(install_dir, env, progress_callback=None):
        """Compiles C++ plugins in src/plugins to the installation's plugins/ directory."""
        if progress_callback: progress_callback("Compilando efectos de video (plugins)...")
        
        # Output directory for plugins
        plugins_out_dir = os.path.join(install_dir, "plugins")
        os.makedirs(plugins_out_dir, exist_ok=True)
        
        # Source directory
        plugins_src_root = os.path.join(install_dir, "src", "plugins")
        if not os.path.exists(plugins_src_root):
            return

        # Common headers
        ofx_include = os.path.abspath(os.path.join(install_dir, "src", "core", "ofx", "include"))
        
        # Walk through each plugin folder
        for plugin_name in os.listdir(plugins_src_root):
            plugin_path = os.path.join(plugins_src_root, plugin_name)
            if not os.path.isdir(plugin_path):
                continue
            
            # Look for a .cpp file with the same name as the folder
            cpp_file = os.path.join(plugin_path, f"{plugin_name}.cpp")
            if not os.path.exists(cpp_file):
                continue
                
            output_ofx = os.path.join(plugins_out_dir, f"{plugin_name}.ofx")
            
            # Using g++ (MinGW) instead of cl.exe for portability inside the installer
            # -shared creates a DLL, which we name .ofx
            try:
                subprocess.run([
                    "g++", "-O2", "-shared", 
                    "-I", ofx_include,
                    cpp_file, "-o", output_ofx
                ], check=True, env=env, cwd=install_dir, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                EnvironmentManager.log_to_file(install_dir, f"Plugin {plugin_name} failed:\n{e.stderr}")
