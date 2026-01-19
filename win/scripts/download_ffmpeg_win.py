import os
import sys
import shutil
import urllib.request
import zipfile
import traceback
from pathlib import Path
import time
import stat
import errno

# URLs for BtbN FFmpeg Builds (compatible with pip-installed ecosystem generally)
# We need Shared for DLLs/EXE and Dev for Headers/LIBs
URL_SHARED = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
URL_DEV = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-dev.zip"

PROJECT_ROOT = Path(__file__).parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external"
FFMPEG_DIR = EXTERNAL_DIR / "ffmpeg"

def cleanup_readonly(func, path, exc):
    """
    Error handler for ``shutil.rmtree``.
    Compatible with Python 3.12+ `onexc` and older `onerror` (via wrapper if needed).
    """
    # handle exception argument difference between onerror (tuple) and onexc (exception instance)
    exc_value = exc
    if isinstance(exc, tuple):
        exc_value = exc[1]
    
    if func in (os.rmdir, os.remove, os.unlink):
        if hasattr(exc_value, 'errno') and exc_value.errno == errno.EACCES:
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
                return
            except Exception:
                pass # If it fails again, we let it propagate in the original flow or just raise

    raise exc_value

def remove_dir_with_retry(path, retries=10, delay=1.0):
    """
    Attempts to remove a directory. If it fails due to locking,
    it waits and retries.
    """
    path = Path(path)
    if not path.exists():
        return

    print(f"Removing directory: {path}")
    
    # Python 3.12+ uses onexc, older uses onerror
    kwargs = {}
    if sys.version_info >= (3, 12):
        kwargs['onexc'] = cleanup_readonly
    else:
        kwargs['onerror'] = cleanup_readonly

    for i in range(retries):
        try:
            if path.is_dir():
                shutil.rmtree(path, **kwargs)
            else:
                try:
                    os.remove(path)
                except PermissionError:
                    os.chmod(path, stat.S_IWRITE)
                    os.remove(path)
            return
        except OSError as e:
            if i < retries - 1:
                print(f"  Attempt {i+1} failed ({e}). Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  Failed to remove {path} after {retries} attempts. Error: {e}")
                print("  Please manually remove this directory if needed.")

def move_with_retry(src, dst, retries=10, delay=1.0):
    """
    Robust move with retry for Windows locking issues.
    """
    print(f"Moving {src} to {dst}")
    for i in range(retries):
        try:
            shutil.move(str(src), str(dst))
            return True
        except OSError as e:
            if i < retries - 1:
                print(f"  Move attempt {i+1} failed ({e}). Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  Failed to move {src} to {dst} after {retries} attempts.")
                raise e

def download_file(url, desc):
    print(f"Downloading {desc}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            file_data = response.read()
            filename = url.split("/")[-1]
            file_path = EXTERNAL_DIR / filename
            with open(file_path, "wb") as f:
                f.write(file_data)
            print(f"Downloaded {filename}")
            return file_path
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def extract_zip(zip_path, target_root_name):
    print(f"Extracting {zip_path.name}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTERNAL_DIR)
            
            # Find the extracted folder name
            extracted_folder = None
            for name in zip_ref.namelist():
                top_level = name.split('/')[0]
                possible_path = EXTERNAL_DIR / top_level
                if possible_path.is_dir() and "ffmpeg" in top_level.lower():
                    extracted_folder = possible_path
                    break
            
            return extracted_folder
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return None

def setup_ffmpeg():
    # Only clean if broken
    if FFMPEG_DIR.exists():
        # Check if it has bin/ffmpeg.exe and include/libavcodec
        if (FFMPEG_DIR / "bin" / "ffmpeg.exe").exists() and (FFMPEG_DIR / "include" / "libavcodec").exists():
            print("FFmpeg appears to be correctly installed.")
            return True
        else:
            print("FFmpeg directory exists but seems incomplete. Reinstalling...")
            remove_dir_with_retry(FFMPEG_DIR)
    
    # Ensure fresh start for these
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    if FFMPEG_DIR.exists():
         remove_dir_with_retry(FFMPEG_DIR)
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download and Process Shared (Binaries & Dev)
    # Note: BtbN shared builds now seem to include headers/libs too, or at least we verified they do.
    zip_shared = download_file(URL_SHARED, "FFmpeg Shared Binaries")
    if not zip_shared: return False
    
    extracted_shared = extract_zip(zip_shared, "shared")
    if extracted_shared:
        # Give OS time to close handles/scan files
        time.sleep(2)
        
        # Move bin to FFMPEG_DIR/bin
        move_with_retry(extracted_shared / "bin", FFMPEG_DIR / "bin")
        
        # Move include to FFMPEG_DIR/include (if exists)
        if (extracted_shared / "include").exists():
            move_with_retry(extracted_shared / "include", FFMPEG_DIR / "include")
        
        # Move lib to FFMPEG_DIR/lib (if exists)
        if (extracted_shared / "lib").exists():
            move_with_retry(extracted_shared / "lib", FFMPEG_DIR / "lib")
        
        # Clean up
        remove_dir_with_retry(extracted_shared)
    else:
        print("Failed to extract shared binaries")
        return False
    
    # Cleanup Zip
    try:
        print("Cleaning up zip file...")
        if zip_shared.exists(): os.remove(zip_shared)
    except Exception as e:
        print(f"Warning: Could not remove zip file: {e}")

    # Verify installation
    if (FFMPEG_DIR / "bin" / "ffmpeg.exe").exists() and (FFMPEG_DIR / "include").exists():
        print("FFmpeg setup complete.")
        return True
    else:
        print("FFmpeg setup incomplete: Missing bin or include.")
        return False

if __name__ == "__main__":
    try:
        success = setup_ffmpeg()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        sys.exit(1)
