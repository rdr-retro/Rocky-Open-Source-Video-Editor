from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QThread, Signal
from gui.pages import WelcomePage, LicensePage, PathPage, ProgressPage, SuccessPage
from core.system import SystemManager
from core.downloader import RepositoryManager
from core.compiler import EnvironmentManager

class InstallWorker(QThread):
    progress = Signal(str)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, target_path, create_shortcut=True):
        super().__init__()
        self.target_path = target_path
        self.create_shortcut = create_shortcut

    def run(self):
        try:
            # 1. Preparations
            self.progress.emit("Iniciando instalación...")
            self.log.emit("Preparando entorno aislado (Python Embebido)...")

            # 2. Download Repo
            REPO_URL = "https://github.com/rdr-retro/Rocky-Open-Source-Video-Editor"
            RepositoryManager.download_repo(REPO_URL, self.target_path, lambda msg: self.progress.emit(msg))
            self.log.emit(f"Repositorio descargado en: {self.target_path}")

            # 3. Setup Env & Compile
            EnvironmentManager.setup_app(self.target_path, lambda msg: self.progress.emit(msg))
            self.log.emit("Compilación C++ exitosa.")
            
            # 4. Create Launcher
            EnvironmentManager.generate_app_exe(self.target_path, lambda msg: self.progress.emit(msg))
            
            # 5. Desktop Shortcut
            if self.create_shortcut:
                self.progress.emit("Creando acceso directo...")
                EnvironmentManager.create_desktop_shortcut(self.target_path)
            
            self.finished.emit(True, "Instalación completada.")
        except Exception as e:
            self.finished.emit(False, str(e))

class InstallerWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocky Editor Setup")
        self.setFixedSize(600, 450)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        
        self.stack = QStackedWidget()
        self.pages = [WelcomePage(), LicensePage(), PathPage(), ProgressPage(), SuccessPage()]
        for p in self.pages: self.stack.addWidget(p)
        
        self.main_layout.addWidget(self.stack)
        
        # Navigation
        nav_frame = QFrame()
        nav_lay = QHBoxLayout(nav_frame)
        self.btn_back = QPushButton("Anterior")
        self.btn_next = QPushButton("Siguiente")
        self.btn_cancel = QPushButton("Cancelar")
        
        self.btn_back.clicked.connect(self._back)
        self.btn_next.clicked.connect(self._next)
        self.btn_cancel.clicked.connect(self.close)
        
        nav_lay.addStretch()
        nav_lay.addWidget(self.btn_back)
        nav_lay.addWidget(self.btn_next)
        nav_lay.addWidget(self.btn_cancel)
        self.main_layout.addWidget(nav_frame)
        
        self._update_nav()

    def _update_nav(self):
        idx = self.stack.currentIndex()
        self.btn_back.setEnabled(idx > 0 and idx < 3)
        self.btn_next.setText("Instalar" if idx == 2 else "Finalizar" if idx == 4 else "Siguiente")
        if idx == 3: # In progress
            self.btn_back.hide()
            self.btn_next.hide()

    def _back(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self._update_nav()

    def _next(self):
        idx = self.stack.currentIndex()
        if idx == 2: # Start Installation
            self._start_install()
        elif idx == 4: # Finish
            self.close()
        else:
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav()

    def _start_install(self):
        self.stack.setCurrentIndex(3)
        self._update_nav()
        path = self.pages[2].path_edit.text()
        shortcut = self.pages[2].check_shortcut.isChecked()
        self.worker = InstallWorker(path, create_shortcut=shortcut)
        self.worker.progress.connect(self.pages[3].status.setText)
        self.worker.log.connect(self.pages[3].log.append)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, success, msg):
        if success:
            self.stack.setCurrentIndex(4)
        else:
            self.pages[3].status.setText(f"ERROR: {msg}")
            self.pages[3].status.setStyleSheet("color: red;")
            self.btn_cancel.setText("Cerrar")
        self._update_nav()
