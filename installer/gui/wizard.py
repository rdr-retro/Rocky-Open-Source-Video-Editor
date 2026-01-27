from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QFrame, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from gui.pages import WelcomePage, LicensePage, PathPage, ProgressPage, SuccessPage
from core.system import SystemManager
from core.downloader import RepositoryManager
from core.compiler import EnvironmentManager

class InstallWorker(QThread):
    progress = Signal(str)
    log = Signal(str)
    finished = Signal(bool, str)
    
    REPO_URL = "https://github.com/rdr-retro/Rocky-Open-Source-Video-Editor"

    def __init__(self, target_path):
        super().__init__()
        self.target_path = target_path

    def run(self):
        try:
            # 1. Pre-flight System Check
            self.progress.emit("Validando sistema (Zero-Error Check)...")
            sys_info = SystemManager.validate_system(self.target_path)
            
            if not sys_info["ok"]:
                raise Exception("\n".join(sys_info["errors"]))
            
            if sys_info["warnings"]:
                for warn in sys_info["warnings"]:
                    self.log.emit(f"ADVERTENCIA: {warn}")
            
            # Auto-fix VC++ if missing
            self.progress.emit("Verificando librerías de Microsoft...")
            SystemManager.install_vcredist_silent(lambda msg: self.progress.emit(msg))
            
            # 2. Extract Bundled Source or Download
            self.progress.emit("Preparando instalación...")
            try:
                RepositoryManager.extract_bundled_repo(self.target_path, lambda msg: self.progress.emit(msg))
            except Exception as e:
                self.log.emit(f"Fallo extracción interna: {e}. Intentando descarga online...")
                self.progress.emit("Descargando última versión desde GitHub...")
                RepositoryManager.download_repo(self.REPO_URL, self.target_path, lambda msg: self.progress.emit(msg))
            
            # 3. Setup Env & Compile
            EnvironmentManager.setup_app(self.target_path, lambda msg: self.progress.emit(msg))
            
            # 4. Create optimized distribution
            EnvironmentManager.generate_app_exe(self.target_path, lambda msg: self.progress.emit(msg))
            
            self.finished.emit(True, "Instalación completada correctamente.")
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
        self.btn_retry = QPushButton("Reintentar")
        self.btn_retry.hide()
        
        self.btn_back.clicked.connect(self._back)
        self.btn_next.clicked.connect(self._next)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_retry.clicked.connect(self._retry)
        
        nav_lay.addWidget(self.btn_retry)
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
            self.btn_cancel.hide()
            self.btn_retry.hide()
        elif idx == 4: # Success
            self.btn_cancel.hide()
            self.btn_back.hide()
            self.btn_next.show()
            self.btn_retry.hide()
        else:
            self.btn_back.show()
            self.btn_next.show()
            self.btn_cancel.show()

    def _back(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self._update_nav()

    def _next(self):
        idx = self.stack.currentIndex()
        if idx == 2: # Start Installation
            self._start_install()
        elif idx == 4: # Finish
            # Create shortcut if requested
            if self.pages[2].check_shortcut.isChecked():
                 path = self.pages[2].path_edit.text()
                 EnvironmentManager.create_desktop_shortcut(path)
            self.close()
        else:
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav()
            
    def _retry(self):
        self.btn_retry.hide()
        self._start_install()

    def _start_install(self):
        self.stack.setCurrentIndex(3)
        self._update_nav()
        
        # Clear previous logs/status
        self.pages[3].status.setText("Iniciando...")
        self.pages[3].status.setStyleSheet("color: #ffffff;")
        self.pages[3].log.clear()
        
        path = self.pages[2].path_edit.text()
        self.worker = InstallWorker(path)
        self.worker.progress.connect(self.pages[3].status.setText)
        self.worker.log.connect(self.pages[3].log.append)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, success, msg):
        if success:
            self.stack.setCurrentIndex(4)
        else:
            # Show friendly error
            self.pages[3].status.setText(f"ERROR CRÍTICO: {msg}\n\nNo te preocupes, el sistema ha guardado un registro.")
            self.pages[3].status.setStyleSheet("color: #ff4d4d; font-weight: bold;")
            self.btn_cancel.show()
            self.btn_cancel.setText("Salir")
            self.btn_retry.show()
            self.btn_retry.setStyleSheet("background-color: #d7cd00; color: black; font-weight: bold;")
            
            QMessageBox.critical(self, "Instalación Fallida", 
                "Ocurrió un error inesperado.\n\n"
                "1. Verifica tu conexión a internet.\n"
                "2. Asegúrate de tener espacio en disco.\n"
                "3. Revisa si un antivirus bloqueó el proceso.\n\n"
                f"Detalle técnico: {msg}"
            )
            
        self._update_nav()
