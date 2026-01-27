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
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Embedded content for RockyBuilder.spec
ROCKY_BUILDER_SPEC_CONTENT = r'''# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['builder_runner.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RockyBuilder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='logo.ico',
)
'''

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

pyinstaller RockyBuilder.spec --clean

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
        self.geometry("800x600")
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

        self.configure_dark_theme()
        self.create_pages()
        self.show_page("WelcomePage")

    def configure_dark_theme(self):
        style = ttk.Style(self)
        style.theme_use('clam')  # 'clam' allows for more color customization

        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        button_bg = "#3c3c3c"
        green_bar = "#00ff00" # Bright Green
        
        self.configure(bg=bg_color)
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=button_bg, foreground=fg_color, borderwidth=1, focuscolor=accent_color)
        style.map("TButton", background=[("active", "#505050")])
        
        style.configure("TEntry", fieldbackground="#404040", foreground=fg_color, insertcolor=fg_color)
        style.configure("TProgressbar", background=green_bar, troughcolor="#2b2b2b", bordercolor=bg_color, thickness=4)
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, focuscolor=bg_color)


    def create_pages(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        for PageClass in (WelcomePage, LicensePage, InstallDirPage, ProgressPage, FinishPage):
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
        
        # Split Welcome Page into two: Image Sidebar (Left) and Content (Right)
        # This is a classic, professional installer layout.
        
        self.sidebar_frame = ttk.Frame(self, width=250)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False) # Keep width fixed
        
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        # Sidebar Image
        self.sidebar_img = None
        try:
            img_path = resource_path("welcome.png")
            if os.path.exists(img_path):
                if HAS_PIL:
                    # Scale to fill the sidebar width and window height
                    pil_img = Image.open(img_path)
                    w, h = pil_img.size
                    ratio = max(250/w, 600/h)
                    new_size = (int(w * ratio), int(h * ratio))
                    pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                    # Center Crop
                    left = (new_size[0] - 250) / 2
                    top = (new_size[1] - 600) / 2
                    self.sidebar_img = ImageTk.PhotoImage(pil_img.crop((left, top, left + 250, top + 600)))
                else:
                    self.sidebar_img = tk.PhotoImage(file=img_path)
                
                img_lbl = ttk.Label(self.sidebar_frame, image=self.sidebar_img, background="#1a1a1a")
                img_lbl.pack(fill="both", expand=True)
            else:
                self.sidebar_frame.configure(style="Footer.TFrame") # Fallback dark background
        except Exception as e:
            print(f"Error loading sidebar image: {e}")
            self.sidebar_frame.configure(style="Footer.TFrame")

        # Content area
        inner_content = ttk.Frame(self.content_frame)
        inner_content.place(relx=0.5, rely=0.5, anchor="center")
        
        label = ttk.Label(inner_content, text="Rocky Video Editor", font=("Segoe UI", 24, "bold"))
        label.pack(pady=(0, 10))
        
        version_lbl = ttk.Label(inner_content, text="Version 0.0.1 ALPHA", font=("Segoe UI", 10), foreground="#888")
        version_lbl.pack(pady=(0, 30))
        
        desc = ttk.Label(inner_content, text="Welcome to the Setup Wizard.\n\nThis will install Rocky Video Editor\non your computer.\n\nClick Next to continue.", 
                         font=("Segoe UI", 12), justify="center")
        desc.pack(pady=10)
        
        btn = ttk.Button(inner_content, text="Next", command=lambda: controller.show_page("LicensePage"), width=20)
        btn.pack(pady=40)

class LicensePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        center_frame = ttk.Frame(self)
        center_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)

        lbl = ttk.Label(center_frame, text="License Agreement", font=("Segoe UI", 16, "bold"))
        lbl.pack(pady=20)
        
        disclaimer = (
            "Descargo de responsabilidad:\n\n"
            "Este software es Open Source y se distribuye tal cual.\n"
            "Garantizamos que no contiene virus y es seguro de usar.\n\n"
            "Al instalar Rocky Video Editor, aceptas estos términos y condiciones."
        )
        
        # Text background wrapper
        text_frame = ttk.Frame(center_frame, padding=2, style="TFrame")
        text_frame.pack(fill="both", expand=True, pady=10)
        
        msg = ttk.Label(text_frame, text=disclaimer, justify="center", wraplength=600, font=("Segoe UI", 11))
        msg.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.var_accept = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(center_frame, text="I accept the terms and conditions", variable=self.var_accept, command=self.toggle_next)
        chk.pack(pady=20)
        
        self.btn_next = ttk.Button(center_frame, text="Next", command=lambda: controller.show_page("InstallDirPage"), state="disabled", width=20)
        self.btn_next.pack(pady=10)

    def toggle_next(self):
        if self.var_accept.get():
            self.btn_next.config(state="normal")
        else:
            self.btn_next.config(state="disabled")

class InstallDirPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        center_frame = ttk.Frame(self)
        center_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)
        
        lbl = ttk.Label(center_frame, text="Select Installation Directory", font=("Segoe UI", 16))
        lbl.pack(pady=20)
        
        input_frame = ttk.Frame(center_frame)
        input_frame.pack(pady=20, fill="x")
        
        self.entry = ttk.Entry(input_frame, textvariable=controller.install_dir, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=3)
        
        btn_browse = ttk.Button(input_frame, text="Browse...", command=self.browse)
        btn_browse.pack(side="right")
        
        btn_next = ttk.Button(center_frame, text="Install", command=lambda: controller.show_page("ProgressPage"), width=20)
        btn_next.pack(pady=30)

    def browse(self):
        directory = filedialog.askdirectory()
        if directory:
            self.controller.install_dir.set(directory)

class ProgressPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # --- AMD Style Layout (Robust Packing) ---
        
        # 3. Footer Area (Packed FIRST at Bottom to ensure visibility)
        footer_style = ttk.Style()
        footer_style.configure("Footer.TFrame", background="#1a1a1a")
        
        self.footer = ttk.Frame(self, style="Footer.TFrame", padding=(20, 15))
        self.footer.pack(fill="x", side="bottom")
        
        # Status Text (Left)
        self.status = tk.StringVar(value="Checking system requirements...")
        self.status_lbl = ttk.Label(self.footer, textvariable=self.status, 
                                    font=("Segoe UI", 10), background="#1a1a1a", foreground="#cccccc")
        self.status_lbl.pack(side="left", anchor="center")
        
        # Cancel Button (Right)
        self.btn_cancel = ttk.Button(self.footer, text="Cancel", command=self.cancel_install)
        self.btn_cancel.pack(side="right", anchor="center")
        
        # 2. Progress Line (Packed SECOND at Bottom, sitting above footer)
        prog_frame = ttk.Frame(self, height=4) 
        prog_frame.pack(fill="x", side="bottom")
        
        self.progress = ttk.Progressbar(prog_frame, orient="horizontal", mode="indeterminate", style="TProgressbar")
        self.progress.pack(fill="x", expand=True)

        # 1. Hero Image Area (Packed LAST, taking remaining space)
        self.img_frame = ttk.Frame(self)
        self.img_frame.pack(fill="both", expand=True, side="top")
        
        self.splash_img = None
        try:
            img_path = resource_path("welcome.png")
            if os.path.exists(img_path):
                if HAS_PIL:
                    # Calculate available space: Window is 800x600
                    # Progress bar + Footer is roughly 50+15+15+4 = 84px
                    # So roughly 800x510
                    pil_img = Image.open(img_path)
                    w, h = pil_img.size
                    
                    # Target size (dynamic would be better but geometry is fixed at 800x600)
                    target_w, target_h = 800, 510
                    
                    # Scale to fit (contain) or fill? 
                    # "Vea bien completa" suggests seeing the whole thing, so "fit" (contain)
                    ratio = min(target_w/w, target_h/h)
                    new_size = (int(w * ratio), int(h * ratio))
                    pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                    self.splash_img = ImageTk.PhotoImage(pil_img)
                else:
                    self.splash_img = tk.PhotoImage(file=img_path)
                
                # Display image centered
                self.img_lbl = ttk.Label(self.img_frame, image=self.splash_img, anchor="center")
                self.img_lbl.pack(fill="both", expand=True)
            else:
                ttk.Label(self.img_frame, text="Installing...", font=("Segoe UI", 24)).pack(pady=50)
        except Exception as e:
            ttk.Label(self.img_frame, text=f"Error loading image: {e}").pack(pady=20)


        # Hidden Log text logic
        self.log_text = tk.Text(self, height=1, width=1, state="disabled") 

        # Start installation on show
        self.bind("<Visibility>", self.start_installation)

    def log(self, message):
        self.status.set(message)
        print(message) 

    def cancel_install(self):
        if messagebox.askyesno("Cancel Installation", "Are you sure you want to cancel?"):
            self.controller.quit()

    def start_installation(self, event):
        if hasattr(self, 'started'): return
        self.started = True
        self.progress.start(10) # Slower, smoother pulse
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
            
            # 4. Inject Scripts & Configs
            self.log("Injecting builder scripts and configs...")
            with open(os.path.join(install_path, "builder_runner.py"), "w", encoding="utf-8") as f:
                f.write(BUILDER_RUNNER_CONTENT)
            
            with open(os.path.join(install_path, "RockyBuilder.spec"), "w", encoding="utf-8") as f:
                f.write(ROCKY_BUILDER_SPEC_CONTENT)
            
            with open(os.path.join(install_path, "make_builder_exe.ps1"), "w", encoding="utf-8") as f:
                f.write(MAKE_BUILDER_EXE_CONTENT)
                
            # Copy logo.ico from installer to install_path for the builder to use
            try:
                if os.path.exists(resource_path('logo.ico')):
                    shutil.copy2(resource_path('logo.ico'), os.path.join(install_path, 'logo.ico'))
            except Exception as e:
                self.log(f"Warning: Could not copy logo.ico: {e}")

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
        
        center_frame = ttk.Frame(self)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl = ttk.Label(center_frame, text="Installation Setup Completed!", font=("Segoe UI", 18, "bold"))
        lbl.pack(pady=30)
        
        desc = ttk.Label(center_frame, text="Rocky Video Editor has been successfully installed.\nA shortcut has been created on your desktop.", 
                         font=("Segoe UI", 11), justify="center")
        desc.pack(pady=10)
        
        btn = ttk.Button(center_frame, text="Finish", command=controller.quit, width=20)
        btn.pack(pady=40)

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
