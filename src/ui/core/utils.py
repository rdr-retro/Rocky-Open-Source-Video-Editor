import sys
import os
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PySide6.QtCore import Qt, QRectF
import rocky_core

def get_resource_path(filename):
    """Get absolute path to resource in src/ui/assets, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        # src/ui/core/utils.py -> ../../.. -> root
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    # Try specific assets folder
    asset_path = os.path.join(base, "src", "ui", "assets", filename)
    if os.path.exists(asset_path):
        return asset_path
        
    # Try root fallback
    root_path = os.path.join(base, filename)
    if os.path.exists(root_path):
        return root_path
        
    return asset_path

def get_rounded_icon(path):
    """On macOS, applies a squircle-style rounding to the icon for better integration."""
    if not os.path.exists(path):
        return QIcon()
        
    original = QPixmap(path)
    if sys.platform != "darwin":
        return QIcon(original)
        
    size = original.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.transparent)
    
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    
    padding = size.width() * 0.09
    content_size = size.width() - (padding * 2)
    radius = content_size * 0.175
    
    path_qt = QPainterPath()
    rect = QRectF(padding, padding, content_size, content_size)
    path_qt.addRoundedRect(rect, radius, radius)
    
    painter.setClipPath(path_qt)
    painter.drawPixmap(rect.toRect(), original)
    
    painter.setClipping(False)
    glass_pen = QPen(QColor(255, 255, 255, 180))
    glass_pen.setWidth(3)
    painter.setPen(glass_pen)
    painter.drawPath(path_qt)
    
    painter.end()
    return QIcon(rounded)

def get_platform_display_info():
    """Returns a formatted string with hardware and OS information."""
    try:
        config = rocky_core.RuntimeConfig.get_instance()
        config.initialize()
        
        platform = config.get_platform_info()
        profile = config.get_optimization_profile()
        
        backend_names = {
            rocky_core.RenderBackend.Software: "CPU",
            rocky_core.RenderBackend.Metal: "Metal",
            rocky_core.RenderBackend.DirectX11: "DX11",
            rocky_core.RenderBackend.DirectX12: "DX12",
            rocky_core.RenderBackend.Vulkan: "Vulkan",
            rocky_core.RenderBackend.CUDA: "CUDA",
            rocky_core.RenderBackend.OpenCL: "OpenCL"
        }
        
        backend = backend_names.get(profile.preferred_backend, "Unknown")
        
        gpu_display = platform.gpu_info.vendor
        if platform.gpu_info.model and platform.gpu_info.model != "Integrated GPU":
            if platform.gpu_info.model not in gpu_display:
                gpu_display = f"{gpu_display} {platform.gpu_info.model}"
            else:
                gpu_display = platform.gpu_info.model
        
        return (f"{platform.os_name} {platform.os_version} | "
                f"{platform.cpu_cores} cores | "
                f"{platform.total_ram_mb // 1024} GB | "
                f"{gpu_display} | "
                f"{backend}")
    except Exception as e:
        return f"Platform: Unknown ({str(e)})"
