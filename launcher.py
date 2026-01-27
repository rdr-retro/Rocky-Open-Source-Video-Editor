import sys
import os

def setup_env():
    """Sets up DLL paths for FFmpeg and ensures root is in sys.path"""
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else application_path
    
    # 1. Register DLL directory for Python 3.8+
    if hasattr(os, 'add_dll_directory'):
        for d in ['external/ffmpeg/bin', 'external/mingw/bin']:
            full = os.path.join(exe_dir, d)
            if os.path.exists(full):
                os.add_dll_directory(full)
    
    # 2. Add to PATH as fallback
    ff_bin = os.path.join(exe_dir, 'external', 'ffmpeg', 'bin')
    os.environ['PATH'] = ff_bin + ';' + os.environ['PATH']
    
    # 3. Ensure we can import src from the root
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
