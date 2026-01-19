import sys
import os

# Helper to find where we are running from
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temporary directory and stores path in _MEIPASS
    application_path = sys._MEIPASS
    
    # On Windows Frozen, explicit DLL headers might be needed if they are in subdirs
    # But usually PyInstaller collects them to root or we add them. 
    # Our rocky_ui.py handles os.add_dll_directory logic for 'external/ffmpeg/bin'
    # IF we mirror that structure in the bundle.
    # In build_exe.bat we will use --add-binary "external/ffmpeg/bin/*;external/ffmpeg/bin"
    # So the path structure inside _MEIPASS will be external/ffmpeg/bin
    # And rocky_ui.py logic (relying on project root) should find it.
    
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Ensure we can import src from the root
sys.path.insert(0, application_path)

if __name__ == "__main__":
    from src.ui.rocky_ui import main
    main()
