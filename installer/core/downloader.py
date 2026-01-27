import os
import urllib.request
import urllib.error
import zipfile
import tempfile
import shutil
import time
import socket

class RepositoryManager:
    @staticmethod
    def download_with_retry(url, target_path, retries=3, progress_callback=None):
        """Robust download with exponential backoff and localized error handling."""
        attempt = 0
        while attempt < retries:
            try:
                if progress_callback:
                    msg = f"Iniciando descarga (Intento {attempt + 1}/{retries})..."
                    if attempt > 0: msg += " Reinesperando..."
                    progress_callback(msg)
                
                # Create request with user agent to avoid some 403s
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                
                with urllib.request.urlopen(req, timeout=30) as response, open(target_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                    
                # Basic validation: check if file is not empty
                if os.path.getsize(target_path) < 1024:
                    raise Exception("El archivo descargado parece corrupto (tamaño muy pequeño).")
                    
                return True
                
            except (urllib.error.URLError, socket.timeout, Exception) as e:
                attempt += 1
                wait_time = 2 ** attempt # Exponential backoff: 2s, 4s, 8s...
                if progress_callback: 
                    progress_callback(f"Error de red: {str(e)}. Reintentando en {wait_time}s...")
                time.sleep(wait_time)
                
        raise Exception(f"Fallo crítico al descargar tras {retries} intentos: {url}")

    @staticmethod
    def download_repo(repo_url, target_dir, progress_callback=None):
        """Downloads the repository ZIP from GitHub and extracts it."""
        if progress_callback: progress_callback("Descargando código fuente desde GitHub...")
        
        # Branch specific ZIP download
        zip_url = f"{repo_url.rstrip('/')}/archive/refs/heads/main.zip"
        extract_path = tempfile.mkdtemp()
        zip_path = os.path.join(extract_path, "repo.zip")
        
        try:
            RepositoryManager.download_with_retry(zip_url, zip_path, progress_callback=progress_callback)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
                # Find the root folder (GitHub ZIPs have ONE root folder)
                contents = zip_ref.namelist()
                root_folder = contents[0].split('/')[0]
                for name in contents:
                    if '/' not in name: continue
                    part = name.split('/')[0]
                    if part and part != root_folder:
                         # Unexpected structure, stick to first detected
                         break
                
                source_path = os.path.join(extract_path, root_folder)
                
                # Move contents to target_dir
                if progress_callback: progress_callback(f"Instalando archivos en {target_dir}...")
                for item in os.listdir(source_path):
                    s = os.path.join(source_path, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                
                # Log verify
                log_path = os.path.join(target_dir, "install_log.txt")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"Files installed to {target_dir}\n")
            
            return True
        except Exception as e:
             # Propagate specific error
             raise e
        finally:
            # Cleanup temp extract path
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path, ignore_errors=True)

    @staticmethod
    def extract_bundled_repo(target_dir, progress_callback=None):
        """Copies the bundled 'src' and other project files from the EXE to target_dir."""
        import sys
        if not getattr(sys, 'frozen', False):
             # For dev testing, just copy from the local folder
             base_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        else:
             base_src = sys._MEIPASS

        if progress_callback: progress_callback("Extrayendo archivos del paquete...")
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # List of items to copy to target_dir
        items_to_copy = ["src", "requirements.txt", "setup.py", "logo.png", "version.txt"]
        
        try:
            for item in items_to_copy:
                s = os.path.join(base_src, item)
                d = os.path.join(target_dir, item)
                if not os.path.exists(s): continue
                
                # Detailed log for large operations
                if progress_callback and item == "src": 
                    progress_callback(f"Descomprimiendo código fuente ({item})...")
                
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            return True
        except Exception as e:
            raise Exception(f"Error al extraer archivos internos: {str(e)}")
