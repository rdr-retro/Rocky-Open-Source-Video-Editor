import os
import sys
import subprocess
import urllib.request
import tempfile
import zipfile
import shutil

class SystemManager:
    @staticmethod
    def check_python_env(target_dir):
        """Checks if the embedded environment is already set up."""
        return os.path.exists(os.path.join(target_dir, "python_env", "python.exe"))

    @staticmethod
    def setup_embedded_python(target_dir, progress_callback=None):
        """Downloads and extracts the official Python Embeddable ZIP."""
        # Python 3.12.7 64-bit Embeddable
        url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip"
        py_dir = os.path.join(target_dir, "python_env")
        os.makedirs(py_dir, exist_ok=True)
        
        tmp_zip = os.path.join(tempfile.gettempdir(), "py_embed.zip")
        if progress_callback: progress_callback("Instalando librerías del sistema...")
        urllib.request.urlretrieve(url, tmp_zip)
        
        if progress_callback: progress_callback("Extrayendo archivos base...")
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(py_dir)

        # 2. Download Dev Headers & Libs (MISSING in embeddable!)
        try:
            if progress_callback: progress_callback("Descargando archivos de desarrollo (Headers/Libs)...")
            nuget_url = "https://www.nuget.org/api/v2/package/python/3.12.7"
            nuget_zip = os.path.join(tempfile.gettempdir(), "py_dev.zip")
            urllib.request.urlretrieve(nuget_url, nuget_zip)
            
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
        if progress_callback: progress_callback("Configurando entorno...")
        pip_script = os.path.join(tempfile.gettempdir(), "get-pip.py")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", pip_script)
        subprocess.run([os.path.join(py_dir, "python.exe"), pip_script], check=True, capture_output=True)
        
        return py_dir
