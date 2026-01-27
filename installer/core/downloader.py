import os
import urllib.request
import zipfile
import tempfile
import shutil

class RepositoryManager:
    @staticmethod
    def download_repo(repo_url, target_dir, progress_callback=None):
        """Downloads the repository ZIP from GitHub and extracts it."""
        if progress_callback: progress_callback("Descargando código fuente desde GitHub...")
        
        # Branch specific ZIP download
        zip_url = f"{repo_url.rstrip('/')}/archive/refs/heads/main.zip"
        extract_path = tempfile.mkdtemp()
        zip_path = os.path.join(extract_path, "repo.zip")
        
        urllib.request.urlretrieve(zip_url, zip_path)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
            # Find the root folder (GitHub ZIPs have ONE root folder)
            # Find the common prefix of all files
            contents = zip_ref.namelist()
            root_folder = contents[0].split('/')[0]
            for name in contents:
                if '/' not in name: continue
                if name.split('/')[0] != root_folder:
                    # Unexpected structure, use first dir found
                    root_folder = contents[0].split('/')[0]
                    break
            
            source_path = os.path.join(extract_path, root_folder)
            
            # Move contents to target_dir
            if progress_callback: progress_callback(f"Moviendo archivos a la carpeta final...")
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(target_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            
            # Cleanup temp extract path
            shutil.rmtree(extract_path, ignore_errors=True)
            
            # Log verify
            with open(os.path.join(target_dir, "install_log.txt"), "a") as f:
                f.write(f"Files moved to {target_dir}:\n")
                f.write("\n".join(os.listdir(target_dir)))
                if os.path.exists(os.path.join(target_dir, "src")):
                    f.write("\nsrc content:\n")
                    f.write("\n".join(os.listdir(os.path.join(target_dir, "src"))))
        
        return True

    @staticmethod
    def extract_bundled_repo(target_dir, progress_callback=None):
        """Copies the bundled 'src' and other project files from the EXE to target_dir."""
        import sys
        if not getattr(sys, 'frozen', False):
             # For dev testing, just copy from the local folder
             base_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        else:
             base_src = sys._MEIPASS

        if progress_callback: progress_callback("Instalando código fuente desde el paquete...")
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # List of items to copy to target_dir
        items_to_copy = ["src", "requirements.txt", "setup.py", "logo.png", "version.txt"]
        
        for item in items_to_copy:
            s = os.path.join(base_src, item)
            d = os.path.join(target_dir, item)
            if not os.path.exists(s): continue
            
            if progress_callback: progress_callback(f"Copiando {item}...")
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        return True
