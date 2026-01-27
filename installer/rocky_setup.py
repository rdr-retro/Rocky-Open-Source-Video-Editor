import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import requests
import zipfile
import os
import shutil
import winshell
from win32com.client import Dispatch
import subprocess
import sys

import pythoncom  # Added import
import ctypes

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Embedded content for builder_runner.py
BUILDER_RUNNER_CONTENT = r'''import subprocess
import sys
import os

def run_powershell_script(script_name):
    """Runs a powershell script and checks for errors."""
    if not os.path.exists(script_name):
        print(f"Error: {script_name} not found in {os.getcwd()}")
        return False
    
    print(f"--- Executing {script_name} ---")
    try:
        # Use powershell -ExecutionPolicy Bypass -File <script>
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_name],
            check=False 
        )
        if result.returncode != 0:
            print(f"Error: {script_name} exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"Exception while running {script_name}: {e}")
        return False

def main():
    # Ensure we are in the script's directory (usually the repo root)
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(application_path)
    print(f"Working directory: {os.getcwd()}")

    if not run_powershell_script("compile.ps1"):
        print("Compilation failed. Aborting run.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    if not run_powershell_script("run.ps1"):
        print("Run execution failed.")
        input("Press Enter to exit...")
        sys.exit(1)

    print("--- Done ---")

if __name__ == "__main__":
    main()
'''

# Embedded content for make_builder_exe.ps1
MAKE_BUILDER_EXE_CONTENT = r'''Write-Host "Creating builder_runner.exe with PyInstaller..."

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..."
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller."
        exit 1
    }
}

pyinstaller --onefile --clean --name "RockyBuilder" builder_runner.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful."
    if (Test-Path "dist\RockyBuilder.exe") {
        Write-Host "Moving executable to root..."
        Move-Item -Path "dist\RockyBuilder.exe" -Destination ".\RockyBuilder.exe" -Force
        Write-Host "RockyBuilder.exe is ready in the root folder."
    }
} else {
    Write-Error "Build failed."
}
'''

PYTHON_URL = "https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe"
REPO_URL = "https://github.com/rdr-retro/Rocky-Open-Source-Video-Editor/archive/refs/heads/main.zip"

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rocky Video Editor Installer")
        self.geometry("500x400")
        self.resizable(False, False)
        
        try:
            # Set AppUserModelID to ensure taskbar icon works independently
            myappid = 'rocky.video.editor.installer.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        try:
            self.iconbitmap(resource_path('logo.ico'))
        except Exception:
            pass  # Icon might not be available in dev mode if not in correct path
        
        try:
            # Also set the png icon for window/taskbar consistency
            logo_png = tk.PhotoImage(file=resource_path('logo.png'))
            self.iconphoto(False, logo_png)
        except Exception:
            pass
        
        self.pages = {}
        self.current_page = None
        self.install_dir = tk.StringVar(value=r"C:\Program Files\RockyEditor")
        
        self.create_pages()
        self.show_page("WelcomePage")

    def create_pages(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        for PageClass in (WelcomePage, InstallDirPage, ProgressPage, FinishPage):
            page_name = PageClass.__name__
            page = PageClass(container, self)
            self.pages[page_name] = page
            page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, page_name):
        self.current_page = self.pages[page_name]
        self.current_page.tkraise()

class WelcomePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        label = ttk.Label(self, text="Welcome to Rocky Video Editor Installer", font=("Helvetica", 16))
        label.pack(pady=40)
        
        desc = ttk.Label(self, text="This wizard will download and install\nRocky Video Editor on your computer.")
        desc.pack(pady=10)
        
        btn = ttk.Button(self, text="Next", command=lambda: controller.show_page("InstallDirPage"))
        btn.pack(side="bottom", pady=20)

class InstallDirPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl = ttk.Label(self, text="Select Installation Directory", font=("Helvetica", 14))
        lbl.pack(pady=20)
        
        frame = ttk.Frame(self)
        frame.pack(pady=10, padx=20, fill="x")
        
        self.entry = ttk.Entry(frame, textvariable=controller.install_dir)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_browse = ttk.Button(frame, text="Browse...", command=self.browse)
        btn_browse.pack(side="right")
        
        btn_next = ttk.Button(self, text="Install", command=lambda: controller.show_page("ProgressPage"))
        btn_next.pack(side="bottom", pady=20)

    def browse(self):
        directory = filedialog.askdirectory()
        if directory:
            self.controller.install_dir.set(directory)

class ProgressPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.lbl = ttk.Label(self, text="Installing...", font=("Helvetica", 14))
        self.lbl.pack(pady=20)
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="indeterminate")
        self.progress.pack(pady=20)
        
        self.status = tk.StringVar(value="Starting...")
        self.status_lbl = ttk.Label(self, textvariable=self.status)
        self.status_lbl.pack(pady=5)
        
        self.log_text = tk.Text(self, height=10, width=50, state="disabled", font=("Consolas", 8))
        self.log_text.pack(pady=10, padx=10)

        # Start installation on show
        self.bind("<Visibility>", self.start_installation)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.status.set(message)

    def start_installation(self, event):
        if hasattr(self, 'started'): return
        self.started = True
        self.progress.start(10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def check_and_install_python(self, install_path):
        try:
            # Check if python is accessible
            subprocess.run(["python", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log("Python is already installed.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("Python not found. Downloading installer...")
            installer_name = "python_installer.exe"
            installer_path = os.path.join(install_path, installer_name)
            
            # Ensure the directory exists for the installer
            os.makedirs(install_path, exist_ok=True)
            
            # Download
            response = requests.get(PYTHON_URL, stream=True)
            with open(installer_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            self.log("Installing Python (this may take a few minutes)...")
            
            # Install silently
            # InstallAllUsers=1: Installs to Program Files
            # PrependPath=1: Adds to PATH
            args = [installer_path, "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"]
            result = subprocess.run(args)
            
            if result.returncode == 0:
                self.log("Python installed successfully.")
                # We need to manually add Python to the current process PATH because
                # the environment update only affects new processes started by Explorer/System.
                # Standard path for All Users install of Python 3.12:
                python_path = r"C:\Program Files\Python312"
                scripts_path = r"C:\Program Files\Python312\Scripts"
                os.environ["PATH"] += os.pathsep + python_path + os.pathsep + scripts_path
            else:
                self.log(f"Warning: Python installer exited with code {result.returncode}")
            
            # Cleanup installer
            if os.path.exists(installer_path):
                os.remove(installer_path)

    def run_install(self):
        pythoncom.CoInitialize()
        install_path = self.controller.install_dir.get()
        
        try:
            # 1. Create Directory (needed early for python installer download if needed)
            self.log(f"Creating directory: {install_path}")
            os.makedirs(install_path, exist_ok=True)

            # Check and Install Python FIRST
            self.check_and_install_python(install_path)

            # 2. Download Repo
            self.log("Downloading repository...")
            zip_path = os.path.join(install_path, "repo.zip")
            response = requests.get(REPO_URL, stream=True)
            with open(zip_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            # 3. Extract
            self.log("Extracting files...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_path)
            
            # Move files from subdirectory to root of install path
            extracted_folder = os.path.join(install_path, "Rocky-Open-Source-Video-Editor-main")
            if os.path.exists(extracted_folder):
                for item in os.listdir(extracted_folder):
                    s = os.path.join(extracted_folder, item)
                    d = os.path.join(install_path, item)
                    if os.path.exists(d):
                        if os.path.isdir(d):
                            shutil.rmtree(d)
                        else:
                            os.remove(d)
                    shutil.move(s, d)
                os.rmdir(extracted_folder)
            
            os.remove(zip_path)
            
            # 4. Inject Scripts
            self.log("Injecting builder scripts...")
            with open(os.path.join(install_path, "builder_runner.py"), "w", encoding="utf-8") as f:
                f.write(BUILDER_RUNNER_CONTENT)
            
            with open(os.path.join(install_path, "make_builder_exe.ps1"), "w", encoding="utf-8") as f:
                f.write(MAKE_BUILDER_EXE_CONTENT)

            # 5. Build Launcher
            self.log("Building launcher (this may take a while)...")
            
            # Use full path to powershell script
            ps_script = os.path.join(install_path, "make_builder_exe.ps1")
            
            # Run the build script
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script],
                cwd=install_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            out, err = process.communicate()
            if process.returncode != 0:
                self.log(f"Build failed: {err}")
                raise Exception(f"Launcher build failed: {err}")
            else:
                self.log("Launcher built successfully.")

            # 6. Create Shortcut
            self.log("Creating Desktop shortcut...")
            desktop = winshell.desktop()
            path = os.path.join(desktop, "Rocky Editor.lnk")
            target = os.path.join(install_path, "RockyBuilder.exe")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = install_path
            shortcut.IconLocation = target
            shortcut.save()
            
            self.log("Installation Complete!")
            self.progress.stop()
            self.controller.after(1000, lambda: self.controller.show_page("FinishPage"))
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.progress.stop()
            messagebox.showerror("Error", str(e))

class FinishPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl = ttk.Label(self, text="Installation Setup Completed!", font=("Helvetica", 16))
        lbl.pack(pady=40)
        
        desc = ttk.Label(self, text="Rocky Video Editor has been successfully installed.\nA shortcut has been created on your desktop.")
        desc.pack(pady=10)
        
        btn = ttk.Button(self, text="Finish", command=controller.quit)
        btn.pack(side="bottom", pady=20)

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
