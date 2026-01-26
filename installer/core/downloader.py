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
        tmp_dir = tempfile.gettempdir()
        zip_path = os.path.join(tmp_dir, "repo.zip")
        
        urllib.request.urlretrieve(zip_url, zip_path)
        
        if progress_callback: progress_callback("Extrayendo archivos...")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
            
            # GitHub ZIPs usually contain a root folder like 'RepoName-main'
            extracted_folder = zip_ref.namelist()[0].split('/')[0]
            source_path = os.path.join(tmp_dir, extracted_folder)
            
            # Move contents to target_dir
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(target_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        
        return True
