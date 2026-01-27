import sys
import os

def setup_env():
    """Sets up DLL paths for FFmpeg and ensures root is in sys.path"""
    # 1. Resolve Project Root
    exe_dir = os.path.dirname(sys.executable)
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else exe_dir
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # Use exe_dir if external/ exists there (Installed mode), else application_path (Dev/Onefile mode)
    root = exe_dir if os.path.isdir(os.path.join(exe_dir, "external")) else application_path
    
    # 2. Register DLL directory for Python 3.8+
    if hasattr(os, 'add_dll_directory'):
        for d in [os.path.join('external', 'ffmpeg', 'bin'), os.path.join('external', 'mingw', 'bin')]:
            full = os.path.join(root, d)
            if os.path.isdir(full):
                try:
                    os.add_dll_directory(full)
                    print(f"Launcher: Added DLL directory {full}")
                except Exception as e:
                    print(f"Launcher Warning: {e}")
    
    # 3. Add to PATH as fallback for subprocesses
    for d in [os.path.join('external', 'ffmpeg', 'bin'), os.path.join('external', 'mingw', 'bin')]:
        full = os.path.join(root, d)
        if os.path.isdir(full):
            if full not in os.environ['PATH']:
                os.environ['PATH'] = full + os.pathsep + os.environ['PATH']
    
    # 4. Ensure we can import src from the root
    if application_path not in sys.path:
        sys.path.insert(0, application_path)
    
    return application_path

if __name__ == "__main__":
    base = setup_env()
    # Import heavy libs AFTER env is ready
    import torch
    import whisper
    import faster_whisper
    
    from src.ui.rocky_ui import main
    main()
