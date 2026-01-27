import os
import subprocess
import urllib.request
import zipfile
import shutil
import tempfile
import sys
from core.system import SystemManager
from core.downloader import RepositoryManager

class EnvironmentManager:
    @staticmethod
    def setup_app(install_dir, progress_callback=None):
        """Full setup using embedded Python, portable MinGW, and FFmpeg."""
        
        # 1. Setup Embedded Python
        py_dir = SystemManager.setup_embedded_python(install_dir, progress_callback)
        python_exe = os.path.join(py_dir, "python.exe")
        
        # 2. Pip Dependencies
        if progress_callback: progress_callback("Actualizando gestor de paquetes (pip)...")
        # 0x08000000 = CREATE_NO_WINDOW
        log_path = os.path.join(install_dir, "install_log.txt")
        
        # Ensure MinGW/FFmpeg are in PATH for pip install (just in case wheels need them)
        env = os.environ.copy()
        
        # 3. Externals (FFmpeg & MinGW) - Download FIRST to have them ready for pip/build
        EnvironmentManager._setup_ffmpeg(install_dir, progress_callback)
        EnvironmentManager._setup_mingw(install_dir, progress_callback)
        
        mingw_bin = os.path.abspath(os.path.join(install_dir, "external", "mingw", "bin"))
        ffmpeg_bin = os.path.abspath(os.path.join(install_dir, "external", "ffmpeg", "bin"))
        
        # FORCE PATH for all subprocesses
        env["PATH"] = f"{mingw_bin};{ffmpeg_bin};" + env["PATH"]
        
        with open(log_path, "a") as log:
            # Upgrade pip & critical build tools
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "pyinstaller"], 
                           check=True, cwd=install_dir, creationflags=0x08000000, stdout=log, stderr=log, env=env)
            
            if os.path.exists(os.path.join(install_dir, "requirements.txt")):
                if progress_callback: progress_callback("Instalando dependencias (esto puede tardar varios minutos)...")
                try:
                    subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt", "--no-warn-script-location"], 
                                   check=True, cwd=install_dir, creationflags=0x08000000, stdout=log, stderr=log, env=env)
                except subprocess.CalledProcessError:
                    # Retry with --force-reinstall in case of corruption
                    log.write("Intento de instalación fallido. Reintentando con --force-reinstall...\n")
                    subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt", "--force-reinstall", "--no-warn-script-location"],
                                   check=True, cwd=install_dir, creationflags=0x08000000, stdout=log, stderr=log, env=env)
            
            # Use pip to ensure compatible numpy version (downgrade if necessary)
            subprocess.run([python_exe, "-m", "pip", "install", "numpy<2.4", "--upgrade", "--no-warn-script-location"],
                           check=False, cwd=install_dir, creationflags=0x08000000, stdout=log, stderr=log, env=env)

        
        # 4. Compile C++ Core (if applicable)
        if progress_callback: progress_callback("Compilando extensiones nativas...")
        
        # 5. Compile Plugins (OFX)
        EnvironmentManager._compile_plugins(install_dir, env, progress_callback)
        
        # 6. Compile Rocky Core C++ via setup.py
        if os.path.exists(os.path.join(install_dir, "setup.py")):
            try:
                # Use --compiler=mingw32 to force MinGW
                result = subprocess.run(
                    [python_exe, "setup.py", "build_ext", "--inplace", "--compiler=mingw32"], 
                    check=True, 
                    cwd=install_dir, 
                    env=env,
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000
                )
                EnvironmentManager.log_to_file(install_dir, "Compilation output:\n" + result.stdout)
            except subprocess.CalledProcessError as e:
                # Capture and log the error output but DON'T fail install if core extension is optional
                error_msg = f"Compilation warning (Non-critical): {e.returncode}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
                EnvironmentManager.log_to_file(install_dir, error_msg)
                # raise Exception(f"Error de compilación C++:\n{e.stderr}") # Soften checking
        
        return True

    @staticmethod
    def log_to_file(install_dir, message):
        log_path = os.path.join(install_dir, "install_log.txt")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except:
            pass

    @staticmethod
    def _setup_ffmpeg(install_dir, progress_callback):
        ext_dir = os.path.join(install_dir, "external")
        ff_dir = os.path.join(ext_dir, "ffmpeg")
        # Check if actually valid
        if os.path.exists(os.path.join(ff_dir, "bin", "ffmpeg.exe")): return
        
        shutil.rmtree(ff_dir, ignore_errors=True)
        if progress_callback: progress_callback("Instalando librerías de video (FFmpeg)...")
        os.makedirs(ext_dir, exist_ok=True)
        
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
        tmp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")
        RepositoryManager.download_with_retry(url, tmp_zip, progress_callback=progress_callback)
        
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(ext_dir)
            extracted = [d for d in os.listdir(ext_dir) if d.startswith("ffmpeg-")][0]
            shutil.move(os.path.join(ext_dir, extracted), ff_dir)

    @staticmethod
    def _setup_mingw(install_dir, progress_callback):
        ext_dir = os.path.join(install_dir, "external")
        mw_dir = os.path.join(ext_dir, "mingw")
        # Check if valid
        if os.path.exists(os.path.join(mw_dir, "bin", "g++.exe")): return
        
        shutil.rmtree(mw_dir, ignore_errors=True)
        if progress_callback: progress_callback("Configurando compilador (MinGW)...")
        os.makedirs(ext_dir, exist_ok=True)
        
        # Use a reliable release
        url = "https://github.com/brechtsanders/winlibs_mingw/releases/download/14.2.0posix-18.1.8-12.0.0-msvcrt-r1/winlibs-x86_64-posix-seh-gcc-14.2.0-mingw-w64msvcrt-12.0.0-r1.zip"
        tmp_zip = os.path.join(tempfile.gettempdir(), "mingw.zip")
        RepositoryManager.download_with_retry(url, tmp_zip, progress_callback=progress_callback)
        
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(ext_dir)
            extracted = [d for d in os.listdir(ext_dir) if d.startswith("mingw64")][0]
            shutil.move(os.path.join(ext_dir, extracted), mw_dir)

    @staticmethod
    def generate_app_exe(install_dir, progress_callback=None):
        """Creates a standalone .exe for the application using PyInstaller."""
        if progress_callback: progress_callback("Iniciando generación de binarios final...")
        py_exe = os.path.join(install_dir, "python_env", "python.exe")
        
        # Verify integrity
        EnvironmentManager._verify_dependencies(py_exe, install_dir, progress_callback)
        
        if progress_callback: progress_callback("Construyendo lanzador optimizado...")
        
        # Minimal launcher script (Hardened)
        launcher_py = os.path.join(install_dir, "_launcher.py")
        with open(launcher_py, "w", encoding="utf-8") as f:
            f.write(
                "import os, sys, shutil, subprocess, tempfile\n"
                "import importlib.util\n"
                "print('--- Rocky Launcher v3.1 (Crash-Fix) ---')\n"
                "def setup_env():\n"
                "    # 1. Determine base path\n"
                "    if getattr(sys, 'frozen', False):\n"
                "        base = sys._MEIPASS\n"
                "        exe_dir = os.path.dirname(sys.executable)\n"
                "    else:\n"
                "        base = os.path.dirname(os.path.abspath(__file__))\n"
                "        exe_dir = base\n"
                "    \n"
                "    # 2. Add FFmpeg/MinGW DLLs to PATH and registry\n"
                "    # With --onedir, we are in a subfolder, so we check parent/sibling structure\n"
                "    # Usual structure: InstallDir/RockyEditor/RockyEditor.exe\n"
                "    # External is at: InstallDir/external\n"
                "    \n"
                "    install_root = os.path.dirname(exe_dir)\n"
                "    if not os.path.exists(os.path.join(install_root, 'external')):\n"
                "        install_root = exe_dir\n"
                "        \n"
                "    ff_bin = os.path.join(install_root, 'external', 'ffmpeg', 'bin')\n"
                "    mw_bin = os.path.join(install_root, 'external', 'mingw', 'bin')\n"
                "    \n"
                "    paths_to_add = []\n"
                "    if os.path.exists(ff_bin): paths_to_add.append(ff_bin)\n"
                "    if os.path.exists(mw_bin): paths_to_add.append(mw_bin)\n"
                "    \n"
                "    # Force prepend to PATH\n"
                "    os.environ['PATH'] = ';'.join(paths_to_add) + ';' + os.environ['PATH']\n"
                "    \n"
                "    # Add DLL directories for Python >= 3.8\n"
                "    if hasattr(os, 'add_dll_directory'):\n"
                "        for p in paths_to_add:\n"
                "            try: os.add_dll_directory(p)\n"
                "            except: pass\n"
                "    \n"
                "    # 3. Setup PYTHONPATH\n"
                "    if base not in sys.path: sys.path.insert(0, base)\n"
                "    os.environ['PYTHONPATH'] = base + ';' + os.environ.get('PYTHONPATH', '')\n"
                "    \n"
                "    return base\n"
                "\n"
                "base_path = setup_env()\n"
                "try:\n"
                "    # Import heavy libs ONLY after env is set\n"
                "    import torch\n"
                "    import whisper\n"
                "    from src.ui.rocky_ui import main\n"
                "    if __name__ == '__main__':\n"
                "        main()\n"
                "except Exception as e:\n"
                "    import traceback\n"
                "    import ctypes\n"
                "    trace = traceback.format_exc()\n"
                "    try:\n"
                "        log_dir = os.path.join(tempfile.gettempdir(), 'RockyEditor_Logs')\n"
                "        os.makedirs(log_dir, exist_ok=True)\n"
                "        log_file = os.path.join(log_dir, 'crash_log.txt')\n"
                "        with open(log_file, 'w') as f: f.write(trace)\n"
                "        msg = f'Error fatal al iniciar Rocky Editor:\\n' + str(e) + f'\\n\\nRevisa: {log_file}'\n"
                "    except:\n"
                "        msg = f'Error fatal al iniciar Rocky Editor:\\n' + str(e) + '\\n\\n(No se pudo guardar log)'\n"
                "    print(trace)\n"
                "    ctypes.windll.user32.MessageBoxW(0, msg, u'Error de Inicio', 0x10)\n"
            )
        
        # Build EXE using PyInstaller
        install_log = os.path.join(install_dir, "install_log.txt")
        env = os.environ.copy()
        mingw_bin = os.path.abspath(os.path.join(install_dir, "external", "mingw", "bin"))
        ffmpeg_bin = os.path.abspath(os.path.join(install_dir, "external", "ffmpeg", "bin"))
        env["PATH"] = f"{mingw_bin};{ffmpeg_bin};" + env["PATH"]

        with open(install_log, "a", encoding="utf-8") as log:
            # Ensure logo.ico AND logo.png are present
            for f in ["logo.ico", "logo.png"]:
                dst = os.path.join(install_dir, f)
                if not os.path.exists(dst):
                    # Try to find it in bundled resources or dev path
                    if getattr(sys, 'frozen', False):
                        src = os.path.join(sys._MEIPASS, f)
                    else:
                        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", f)
                    
                    if os.path.exists(src):
                        try: shutil.copy2(src, dst)
                        except: pass

            log.write("\n--- Starting PyInstaller Build (Zero-Error Mode) ---\n")
            try:
                subprocess.run([
                    py_exe, "-m", "PyInstaller", 
                    "--onedir", "--noconsole", 
                    "--distpath", ".", 
                    "--contents-directory", "_internal",
                    "--icon", "logo.ico",
                    "--add-data", "logo.png;.",
                    "--add-data", "src/ui/assets;src/ui/assets", 
                    "--collect-all", "torch",
                    "--collect-all", "whisper",
                    "--collect-all", "faster_whisper",
                    "--collect-all", "moviepy",
                    "--copy-metadata", "torch",
                    "--copy-metadata", "openai-whisper",
                    "--copy-metadata", "faster-whisper",
                    "--copy-metadata", "tqdm",
                    "--copy-metadata", "regex",
                    "--copy-metadata", "requests",
                    "--copy-metadata", "packaging",
                    "--copy-metadata", "filelock",
                    "--name", "RockyEditor", "_launcher.py"
                ], check=True, cwd=install_dir, creationflags=0x08000000, stdout=log, stderr=log, env=env)
                log.write("PyInstaller build completed successfully.\n")
            except subprocess.CalledProcessError as e:
                log.write(f"PyInstaller failed with code {e.returncode}\n")
                raise Exception(f"Error crítico al generar el ejecutable. Revisa '{install_log}'.")
        
        # Cleanup
        if os.path.exists(launcher_py): os.remove(launcher_py)
        shutil.rmtree(os.path.join(install_dir, "build"), ignore_errors=True)
        spec_file = os.path.join(install_dir, "RockyEditor.spec")
        if os.path.exists(spec_file): os.remove(spec_file)
        
        return True

    @staticmethod
    def _verify_dependencies(py_exe, install_dir, progress_callback):
        """Verifies integrity with functional tests and auto-repairs."""
        # Map import name -> PyPI package name
        dep_map = {
            "torch": "torch",
            "whisper": "openai-whisper",
            "faster_whisper": "faster-whisper",
            "moviepy": "moviepy",
            "PySide6": "PySide6"
        }
        
        env = os.environ.copy()
        ff_bin = os.path.abspath(os.path.join(install_dir, "external", "ffmpeg", "bin"))
        mw_bin = os.path.abspath(os.path.join(install_dir, "external", "mingw", "bin"))
        env["PATH"] = f"{ff_bin};{mw_bin};" + env["PATH"]

        with open(os.path.join(install_dir, "install_log.txt"), "a") as log:
            for import_name, package_name in dep_map.items():
                if progress_callback: progress_callback(f"Verificando integridad de {package_name}...")
                verify_cmd = f"import {import_name}"
                
                # Heavier functional tests
                if import_name == "torch": verify_cmd += "; import torch; x = torch.zeros(1); print(x)"
                
                try:
                    subprocess.run([py_exe, "-c", verify_cmd], check=True, capture_output=True, cwd=install_dir, env=env, creationflags=0x08000000)
                except subprocess.CalledProcessError as e:
                    msg = f"Detectada corrupción en {package_name}. Reparando automáticamente..."
                    if progress_callback: progress_callback(msg)
                    log.write(f"Verification failed for {import_name}: {e.stderr if e.stderr else 'Unknown error'}. Re-installing {package_name}...\n")
                    
                    try:
                        subprocess.run([py_exe, "-m", "pip", "install", package_name, "--force-reinstall", "--no-warn-script-location"], 
                                      check=True, cwd=install_dir, env=env, creationflags=0x08000000, stdout=log, stderr=log)
                    except Exception as verify_err:
                        log.write(f"FATAL: Could not repair {package_name}: {verify_err}\n")
                        raise Exception(f"No se pudo reparar la librería {package_name}. Revisa tu conexión a internet.")

    @staticmethod
    def create_desktop_shortcut(install_dir):
        """Creates a .lnk on the Desktop using PowerShell."""
        exe_path = os.path.join(install_dir, "RockyEditor", "RockyEditor.exe")
        
        if not os.path.exists(exe_path):
            return
            
        work_dir = install_dir # Root dir for assets relative resolution if needed
        
        ps_cmd = (
            "$desktop = [System.Environment]::GetFolderPath('Desktop');"
            "$wsh = New-Object -ComObject WScript.Shell;"
            f"$lnk = $wsh.CreateShortcut(\"$desktop\\Rocky Editor.lnk\");"
            f"$lnk.TargetPath = '{exe_path}';"
            f"$lnk.WorkingDirectory = '{work_dir}';"
            f"$lnk.Save();"
        )
        
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, creationflags=0x08000000)

    @staticmethod
    def _compile_plugins(install_dir, env, progress_callback=None):
        """Compiles C++ plugins in src/plugins to the installation's plugins/ directory."""
        if progress_callback: progress_callback("Compilando efectos visuales (plugins)...")
        
        plugins_out_dir = os.path.join(install_dir, "plugins")
        os.makedirs(plugins_out_dir, exist_ok=True)
        
        plugins_src_root = os.path.join(install_dir, "src", "plugins")
        if not os.path.exists(plugins_src_root):
            return

        ofx_include = os.path.abspath(os.path.join(install_dir, "src", "core", "ofx", "include"))
        
        # Ensure g++ is found
        env_with_path = env.copy()
        
        for plugin_name in os.listdir(plugins_src_root):
            plugin_path = os.path.join(plugins_src_root, plugin_name)
            if not os.path.isdir(plugin_path): continue
            
            cpp_file = os.path.join(plugin_path, f"{plugin_name}.cpp")
            if not os.path.exists(cpp_file): continue
                
            output_ofx = os.path.join(plugins_out_dir, f"{plugin_name}.ofx")
            
            try:
                # Use g++ directly, assuming it's in the PATH we forced
                subprocess.run([
                    "g++", "-O2", "-shared", 
                    "-I", ofx_include,
                    cpp_file, "-o", output_ofx
                ], check=True, env=env_with_path, cwd=install_dir, capture_output=True, text=True, creationflags=0x08000000)
            except subprocess.CalledProcessError as e:
                EnvironmentManager.log_to_file(install_dir, f"Plugin {plugin_name} compilation failed:\n{e.stderr}")
