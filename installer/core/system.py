import os
import sys
import subprocess
import urllib.request
import tempfile
import zipfile
import shutil
import ctypes
from core.downloader import RepositoryManager

class SystemManager:
    @staticmethod
    def validate_system(install_path):
        """Aggressive pre-flight checks for a zero-error installation."""
        results = {"ok": True, "errors": [], "warnings": []}
        
        # 1. Architecture Check (Only x64 supported for Torch/Whisper)
        import platform
        if platform.machine().lower() not in ["amd64", "x86_64"]:
            results["ok"] = False
            results["errors"].append("Arquitectura incompatible. Se requiere Windows de 64 bits.")
            
        # 2. Disk Space Check (Requires ~5GB for full whisper/torch install)
        # Check install_path drive
        drive = os.path.splitdrive(os.path.abspath(install_path))[0]
        if not drive: drive = "C:"
        
        try:
            total, used, free = shutil.disk_usage(drive)
            if free < 5 * 1024 * 1024 * 1024:
                results["ok"] = False
                results["errors"].append(f"Espacio insuficiente en {drive}. Se requieren al menos 5GB libres.")
        except Exception as e:
            results["warnings"].append(f"No se pudo verificar el espacio en disco: {e}")
            
        # 3. Process Conflict Check
        if SystemManager._is_process_running("RockyEditor.exe"):
             results["ok"] = False
             results["errors"].append("Rocky Editor se está ejecutando. Por favor, ciérralo antes de continuar.")

        # 4. Write Permission Check
        try:
            os.makedirs(install_path, exist_ok=True)
            test_file = os.path.join(install_path, ".write_test")
            with open(test_file, "w") as f: f.write("ok")
            os.remove(test_file)
        except Exception:
            results["ok"] = False
            results["errors"].append(f"No hay permisos de escritura en: {install_path}. Prueba a ejecutar como Administrador.")

        # 5. VC++ Redistributable Check
        if not SystemManager._is_vcredist_installed():
            results["warnings"].append("Falta 'Microsoft Visual C++ Redistributable'. Se intentará instalar automáticamente.")
            
        return results

    @staticmethod
    def _is_process_running(process_name):
        """Checks if a process is running using tasklist."""
        try:
            output = subprocess.check_output(["tasklist", "/FI", f"IMAGENAME eq {process_name}"], creationflags=0x08000000)
            return process_name.lower() in str(output).lower()
        except:
            return False

    @staticmethod
    def _is_vcredist_installed():
        """Checks registry for VC++ 2015-2022 Redistributable."""
        import winreg
        keys = [
            r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
            r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
        ]
        for key_path in keys:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                installed, _ = winreg.QueryValueEx(key, "Installed")
                if installed: return True
            except:
                continue
        return False

    @staticmethod
    def install_vcredist_silent(progress_callback=None):
        """Downloads and installs VC++ Redistributable silently."""
        if progress_callback: progress_callback("Corrigiendo dependencias del sistema (VC++)...")
        url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        tmp_exe = os.path.join(tempfile.gettempdir(), "vc_redist.exe")
        
        try:
            RepositoryManager.download_with_retry(url, tmp_exe, progress_callback=progress_callback)
            # /install /quiet /norestart
            subprocess.run([tmp_exe, "/install", "/quiet", "/norestart"], check=True, creationflags=0x08000000)
        except Exception as e:
            # Don't fail the whole install, just warn
            if progress_callback: progress_callback(f"Advertencia: Falló instalación de VC++: {e}")

    @staticmethod
    def setup_embedded_python(target_dir, progress_callback=None):
        """Downloads and extracts the official Python Embeddable ZIP."""
        # Python 3.12.7 64-bit Embeddable
        url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip"
        py_dir = os.path.join(target_dir, "python_env")
        if os.path.exists(py_dir):
            if os.path.exists(os.path.join(py_dir, "python.exe")):
                return py_dir # Already installed
        
        os.makedirs(py_dir, exist_ok=True)
        
        tmp_zip = os.path.join(tempfile.gettempdir(), "py_embed.zip")
        RepositoryManager.download_with_retry(url, tmp_zip, progress_callback=progress_callback)
        
        if progress_callback: progress_callback("Extrayendo Python embebido...")
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(py_dir)

        # 2. Download Dev Headers & Libs (MISSING in embeddable!)
        try:
            if progress_callback: progress_callback("Descargando componentes de desarrollo...")
            nuget_url = "https://www.nuget.org/api/v2/package/python/3.12.7"
            nuget_zip = os.path.join(tempfile.gettempdir(), "py_dev.zip")
            RepositoryManager.download_with_retry(nuget_url, nuget_zip, progress_callback=progress_callback)
            
            with zipfile.ZipFile(nuget_zip, 'r') as z:
                # Extract 'tools/include' to 'python_env/include'
                # Extract 'tools/libs' to 'python_env/libs'
                for info in z.infolist():
                    if info.filename.startswith("tools/include/"):
                        dest = os.path.join(py_dir, "include", info.filename[len("tools/include/"):])
                        if not info.is_dir():
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with z.open(info) as src, open(dest, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                    elif info.filename.startswith("tools/libs/"):
                        dest = os.path.join(py_dir, "libs", info.filename[len("tools/libs/"):])
                        if not info.is_dir():
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with z.open(info) as src, open(dest, "wb") as dst:
                                shutil.copyfileobj(src, dst)
        except Exception as e:
            if progress_callback: progress_callback(f"Advertencia: No se pudieron bajar los headers: {e}")
            
        # IMPORTANT: Enable site-packages in the embedded distribution
        # We need to uncomment 'import site' in the ._pth file
        pth_file = os.path.join(py_dir, "python312._pth")
        if os.path.exists(pth_file):
            with open(pth_file, "r") as f:
                lines = f.readlines()
            with open(pth_file, "w") as f:
                for line in lines:
                    if "import site" in line:
                        f.write("import site\n")
                    else:
                        f.write(line)
        
        # Install PIP for the embedded environment
        if progress_callback: progress_callback("Instalando pip...")
        pip_script = os.path.join(tempfile.gettempdir(), "get-pip.py")
        RepositoryManager.download_with_retry("https://bootstrap.pypa.io/get-pip.py", pip_script, progress_callback=progress_callback)
        
        # 0x08000000 = CREATE_NO_WINDOW
        subprocess.run([os.path.join(py_dir, "python.exe"), pip_script, "--no-warn-script-location"], check=True, capture_output=True, creationflags=0x08000000)
        
        return py_dir
