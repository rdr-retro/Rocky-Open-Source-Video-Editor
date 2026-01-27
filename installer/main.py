import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.wizard import InstallerWizard

def main():
    app = QApplication(sys.argv)
    
    # Dark Professional setup styling
    app.setStyleSheet("""
        QMainWindow { background-color: #121212; color: #ffffff; }
        QWidget { background-color: #121212; color: #ffffff; font-family: 'Segoe UI', Arial; font-size: 13px; }
        QLabel { color: #ffffff; }
        QTextEdit, QLineEdit { 
            background-color: #1e1e1e; 
            color: #ffffff; 
            border: 1px solid #333333; 
            padding: 5px;
        }
        QPushButton { 
            padding: 8px 25px; 
            border-radius: 4px; 
            background-color: #2d2d2d;
            border: 1px solid #444444;
            color: #ffffff;
        }
        QPushButton:hover { background-color: #3d3d3d; border: 1px solid #0078d7; }
        QPushButton#primary { 
            background-color: #0078d7; 
            color: white; 
            font-weight: bold; 
            border: none;
        }
        QPushButton#primary:hover { background-color: #005a9e; }
        QProgressBar { 
            border: 1px solid #333; 
            border-radius: 2px; 
            text-align: center; 
            height: 25px; 
            background: #1e1e1e;
            color: #ffffff;
        }
        QProgressBar::chunk { background-color: #06b025; }
        QCheckBox { color: #ffffff; }
    """)
    
    window = InstallerWizard()
    
    # Taskbar Icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
