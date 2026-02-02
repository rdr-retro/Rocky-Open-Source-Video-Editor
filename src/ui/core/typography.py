"""
Rocky Video Editor - Advanced Typography System
Blender-style font management with Inter typeface and HiDPI support.
"""

from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtCore import QSettings
import os
from pathlib import Path
from typing import Optional, Dict


class ThemeTypography:
    """
    Advanced typography management system with vectorial scaling.
    Emulates Blender's high-quality text rendering approach.
    """
    
    # Base configuration (at 1.0 scale)
    BASE_UI_FONT_SIZE = 11
    BASE_UI_LINE_HEIGHT = 1.4  # Multiplier
    BASE_CHARACTER_SPACING = 0  # Letter spacing in pixels
    
    # Font weights
    WEIGHT_REGULAR = QFont.Weight.Normal
    WEIGHT_MEDIUM = QFont.Weight.Medium
    WEIGHT_BOLD = QFont.Weight.Bold
    
    def __init__(self, display_scale: float = 1.0):
        """
        Initialize typography system.
        
        Args:
            display_scale: Global UI scale factor (1.0 = 100%, 1.5 = 150%, etc.)
        """
        self.display_scale = display_scale
        self._font_ids: Dict[str, int] = {}
        self._fonts_loaded = False
        
        # Paths to Inter font files
        self.font_dir = Path(__file__).parent.parent / "fonts"
        self.inter_regular = self.font_dir / "Inter-Regular.ttf"
        self.inter_medium = self.font_dir / "Inter-Medium.ttf"
        self.inter_bold = self.font_dir / "Inter-Bold.ttf"
        
        # Load fonts
        self._load_fonts()
        
    def _load_fonts(self) -> bool:
        """
        Load Inter font files into Qt font database.
        
        Returns:
            True if fonts loaded successfully, False otherwise
        """
        font_db = QFontDatabase()
        
        # Ensure font directory exists
        if not self.font_dir.exists():
            self.font_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Typography] Font directory created: {self.font_dir}")
            return False
        
        # Load each font variant
        fonts_to_load = [
            ("Inter-Regular", self.inter_regular),
            ("Inter-Medium", self.inter_medium),
            ("Inter-Bold", self.inter_bold)
        ]
        
        for font_name, font_path in fonts_to_load:
            if font_path.exists():
                font_id = font_db.addApplicationFont(str(font_path))
                if font_id != -1:
                    self._font_ids[font_name] = font_id
                    families = font_db.applicationFontFamilies(font_id)
                    print(f"[Typography] Loaded {font_name}: {families}")
                else:
                    print(f"[Typography] Failed to load {font_name}")
            else:
                print(f"[Typography] Font file not found: {font_path}")
        
        self._fonts_loaded = len(self._font_ids) > 0
        return self._fonts_loaded
    
    @property
    def ui_font_size(self) -> int:
        """Get scaled UI font size."""
        return int(self.BASE_UI_FONT_SIZE * self.display_scale)
    
    @property
    def ui_line_height(self) -> int:
        """Get scaled line height in pixels."""
        return int(self.ui_font_size * self.BASE_UI_LINE_HEIGHT)
    
    @property
    def character_spacing(self) -> int:
        """Get scaled character spacing."""
        return int(self.BASE_CHARACTER_SPACING * self.display_scale)
    
    def get_font(self, 
                 size: Optional[int] = None, 
                 weight: QFont.Weight = QFont.Weight.Normal,
                 use_fallback: bool = True) -> QFont:
        """
        Get a configured QFont with proper hinting and antialiasing.
        
        Args:
            size: Font size in points (None = use default ui_font_size)
            weight: Font weight (Normal, Medium, Bold)
            use_fallback: Use system fallback if Inter not available
            
        Returns:
            Configured QFont instance
        """
        if size is None:
            size = self.ui_font_size
        else:
            size = int(size * self.display_scale)
        
        # Try to use Inter font
        if self._fonts_loaded:
            font = QFont("Inter", size, weight)
        elif use_fallback:
            # Fallback to system sans-serif
            font = QFont("Sans Serif", size, weight)
            print("[Typography] Using fallback font: Sans Serif")
        else:
            font = QFont("Inter", size, weight)
        
        # Configure for optimal rendering (Blender-style)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        font.setKerning(True)
        
        # Apply letter spacing if configured
        if self.character_spacing != 0:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, self.character_spacing)
        
        return font
    
    def get_font_metrics(self, font: Optional[QFont] = None) -> QFontMetrics:
        """
        Get font metrics for layout calculations.
        
        Args:
            font: QFont instance (None = use default UI font)
            
        Returns:
            QFontMetrics instance
        """
        if font is None:
            font = self.get_font()
        return QFontMetrics(font)
    
    def set_display_scale(self, scale: float):
        """
        Update global display scale factor.
        
        Args:
            scale: New scale factor (1.0 = 100%)
        """
        self.display_scale = max(0.5, min(3.0, scale))  # Clamp between 50% and 300%
        print(f"[Typography] Display scale set to {self.display_scale * 100:.0f}%")
    
    def get_css_font_family(self) -> str:
        """
        Get CSS-compatible font-family string with fallbacks.
        
        Returns:
            Font family string for QSS/CSS
        """
        if self._fonts_loaded:
            return "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif"
        else:
            return "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif"
    
    def generate_qss_variables(self) -> str:
        """
        Generate QSS stylesheet with typography variables.
        
        Returns:
            QSS string with font definitions
        """
        return f"""
            * {{
                font-family: {self.get_css_font_family()};
                font-size: {self.ui_font_size}px;
            }}
            
            QLabel {{
                font-size: {self.ui_font_size}px;
                line-height: {self.ui_line_height}px;
            }}
            
            QPushButton {{
                font-size: {self.ui_font_size}px;
                font-weight: 500;
            }}
            
            QMenu {{
                font-size: {self.ui_font_size}px;
            }}
            
            QMenuBar {{
                font-size: {self.ui_font_size}px;
            }}
        """
    
    @staticmethod
    def download_inter_fonts(target_dir: Path) -> bool:
        """
        Helper method to download Inter fonts from Google Fonts or GitHub.
        
        Args:
            target_dir: Directory to save font files
            
        Returns:
            True if download successful
        """
        print("[Typography] Auto-download not implemented.")
        print("[Typography] Please download Inter fonts manually from:")
        print("  https://github.com/rsms/inter/releases")
        print(f"  and place them in: {target_dir}")
        return False


# Global typography instance
_typography_instance: Optional[ThemeTypography] = None


def get_typography(display_scale: float = 1.0) -> ThemeTypography:
    """
    Get or create global typography instance.
    
    Args:
        display_scale: Display scale factor (only used on first call)
        
    Returns:
        ThemeTypography singleton instance
    """
    global _typography_instance
    if _typography_instance is None:
        _typography_instance = ThemeTypography(display_scale)
    return _typography_instance


def set_global_display_scale(scale: float):
    """
    Set global display scale for all typography.
    
    Args:
        scale: Scale factor (1.0 = 100%)
    """
    typo = get_typography()
    typo.set_display_scale(scale)


# Convenience functions for common use cases
def get_ui_font(size: Optional[int] = None) -> QFont:
    """Get standard UI font."""
    return get_typography().get_font(size, QFont.Weight.Normal)


def get_bold_font(size: Optional[int] = None) -> QFont:
    """Get bold UI font."""
    return get_typography().get_font(size, QFont.Weight.Bold)


def get_medium_font(size: Optional[int] = None) -> QFont:
    """Get medium weight UI font."""
    return get_typography().get_font(size, QFont.Weight.Medium)
