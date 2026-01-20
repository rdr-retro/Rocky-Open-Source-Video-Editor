"""
Rocky Video Editor - Premium Design System
Curated HSL color palettes for a professional, modern dark mode interface.
"""

from PySide6.QtGui import QColor

# ============================================================================
# CORE COLOR SCIENCE - HSL Based System
# ============================================================================

def hsl_to_qcolor(h: int, s: int, l: int, a: int = 255) -> QColor:
    """
    Convert HSL values to QColor.
    
    Args:
        h: Hue (0-359)
        s: Saturation (0-100)
        l: Lightness (0-100)
        a: Alpha (0-255)
    """
    color = QColor()
    color.setHsl(h, int(s * 2.55), int(l * 2.55), a)
    return color

def hsl_to_hex(h: int, s: int, l: int) -> str:
    """Convert HSL to hex string for QSS."""
    color = hsl_to_qcolor(h, s, l)
    return color.name()


# ============================================================================
# PALETTE 1: MIDNIGHT SLATE (Primary Dark Theme)
# Professional, cinematic dark mode with deep blues and purples
# ============================================================================

class MidnightSlate:
    """Deep, cinematic color scheme inspired by professional video editing suites."""
    
    # Background Layers (Depth Hierarchy)
    BG_DEEPEST = hsl_to_hex(220, 18, 12)      # HSL(220, 18%, 12%) - Canvas base
    BG_DEEP = hsl_to_hex(220, 16, 15)         # HSL(220, 16%, 15%) - Panels
    BG_MEDIUM = hsl_to_hex(220, 14, 18)       # HSL(220, 14%, 18%) - Cards
    BG_ELEVATED = hsl_to_hex(220, 12, 22)     # HSL(220, 12%, 22%) - Hover states
    
    # Accent Colors (Vibrant, High Contrast)
    ACCENT_PRIMARY = hsl_to_hex(195, 85, 55)  # HSL(195, 85%, 55%) - Cyan blue
    ACCENT_SECONDARY = hsl_to_hex(270, 70, 65) # HSL(270, 70%, 65%) - Purple
    ACCENT_SUCCESS = hsl_to_hex(145, 65, 55)  # HSL(145, 65%, 55%) - Emerald green
    ACCENT_WARNING = hsl_to_hex(35, 90, 60)   # HSL(35, 90%, 60%) - Warm amber
    ACCENT_ERROR = hsl_to_hex(355, 75, 60)    # HSL(355, 75%, 60%) - Coral red
    
    # UI Elements
    BORDER_SUBTLE = hsl_to_hex(220, 10, 28)   # HSL(220, 10%, 28%)
    BORDER_DEFAULT = hsl_to_hex(220, 12, 35)  # HSL(220, 12%, 35%)
    BORDER_STRONG = hsl_to_hex(220, 15, 45)   # HSL(220, 15%, 45%)
    
    # Text Hierarchy
    TEXT_PRIMARY = hsl_to_hex(220, 15, 95)    # HSL(220, 15%, 95%) - Almost white
    TEXT_SECONDARY = hsl_to_hex(220, 10, 75)  # HSL(220, 10%, 75%) - Muted
    TEXT_TERTIARY = hsl_to_hex(220, 8, 55)    # HSL(220, 8%, 55%) - Subtle
    TEXT_DISABLED = hsl_to_hex(220, 5, 40)    # HSL(220, 5%, 40%) - Faded
    
    # Track Colors (Video/Audio distinction)
    TRACK_VIDEO_ACCENT = hsl_to_hex(340, 60, 50)    # HSL(340, 60%, 50%) - Deep rose
    TRACK_VIDEO_BODY = hsl_to_hex(340, 55, 35)      # HSL(340, 55%, 35%) - Darker rose
    TRACK_AUDIO_ACCENT = hsl_to_hex(180, 55, 50)    # HSL(180, 55%, 50%) - Teal
    TRACK_AUDIO_BODY = hsl_to_hex(180, 50, 35)      # HSL(180, 50%, 35%) - Darker teal


# ============================================================================
# PALETTE 2: OBSIDIAN GOLD (Alternative Warm Theme)
# Warm, luxurious dark mode with gold and amber accents
# ============================================================================

class ObsidianGold:
    """Warm, premium color scheme with gold accents."""
    
    # Background Layers
    BG_DEEPEST = hsl_to_hex(30, 12, 10)       # HSL(30, 12%, 10%) - Warm black
    BG_DEEP = hsl_to_hex(30, 10, 14)          # HSL(30, 10%, 14%)
    BG_MEDIUM = hsl_to_hex(30, 8, 18)         # HSL(30, 8%, 18%)
    BG_ELEVATED = hsl_to_hex(30, 6, 24)       # HSL(30, 6%, 24%)
    
    # Accent Colors
    ACCENT_PRIMARY = hsl_to_hex(45, 85, 60)   # HSL(45, 85%, 60%) - Gold
    ACCENT_SECONDARY = hsl_to_hex(25, 75, 55) # HSL(25, 75%, 55%) - Copper
    ACCENT_SUCCESS = hsl_to_hex(140, 60, 50)  # HSL(140, 60%, 50%) - Jade
    ACCENT_WARNING = hsl_to_hex(35, 95, 65)   # HSL(35, 95%, 65%) - Amber
    ACCENT_ERROR = hsl_to_hex(5, 80, 60)      # HSL(5, 80%, 60%) - Vermillion
    
    # UI Elements
    BORDER_SUBTLE = hsl_to_hex(30, 8, 25)
    BORDER_DEFAULT = hsl_to_hex(30, 10, 32)
    BORDER_STRONG = hsl_to_hex(30, 12, 42)
    
    # Text
    TEXT_PRIMARY = hsl_to_hex(30, 8, 92)
    TEXT_SECONDARY = hsl_to_hex(30, 6, 72)
    TEXT_TERTIARY = hsl_to_hex(30, 5, 52)
    TEXT_DISABLED = hsl_to_hex(30, 4, 38)
    
    # Track Colors
    TRACK_VIDEO_ACCENT = hsl_to_hex(320, 55, 55)
    TRACK_VIDEO_BODY = hsl_to_hex(320, 50, 38)
    TRACK_AUDIO_ACCENT = hsl_to_hex(165, 50, 55)
    TRACK_AUDIO_BODY = hsl_to_hex(165, 45, 38)


# ============================================================================
# PALETTE 3: ARCTIC NIGHT (Cool Blue Theme)
# Clean, modern theme with icy blues and crisp whites
# ============================================================================

class ArcticNight:
    """Cool, clean color scheme with arctic blue tones."""
    
    # Background Layers
    BG_DEEPEST = hsl_to_hex(210, 20, 11)      # HSL(210, 20%, 11%)
    BG_DEEP = hsl_to_hex(210, 18, 14)         # HSL(210, 18%, 14%)
    BG_MEDIUM = hsl_to_hex(210, 16, 17)       # HSL(210, 16%, 17%)
    BG_ELEVATED = hsl_to_hex(210, 14, 21)     # HSL(210, 14%, 21%)
    
    # Accent Colors
    ACCENT_PRIMARY = hsl_to_hex(190, 90, 58)  # HSL(190, 90%, 58%) - Ice blue
    ACCENT_SECONDARY = hsl_to_hex(260, 65, 60) # HSL(260, 65%, 60%) - Lavender
    ACCENT_SUCCESS = hsl_to_hex(150, 70, 52)  # HSL(150, 70%, 52%) - Mint
    ACCENT_WARNING = hsl_to_hex(40, 88, 62)   # HSL(40, 88%, 62%) - Sunlight
    ACCENT_ERROR = hsl_to_hex(350, 78, 62)    # HSL(350, 78%, 62%) - Rose
    
    # UI Elements
    BORDER_SUBTLE = hsl_to_hex(210, 12, 26)
    BORDER_DEFAULT = hsl_to_hex(210, 14, 34)
    BORDER_STRONG = hsl_to_hex(210, 16, 44)
    
    # Text
    TEXT_PRIMARY = hsl_to_hex(210, 18, 96)
    TEXT_SECONDARY = hsl_to_hex(210, 12, 76)
    TEXT_TERTIARY = hsl_to_hex(210, 10, 56)
    TEXT_DISABLED = hsl_to_hex(210, 8, 42)
    
    # Track Colors
    TRACK_VIDEO_ACCENT = hsl_to_hex(330, 58, 52)
    TRACK_VIDEO_BODY = hsl_to_hex(330, 52, 36)
    TRACK_AUDIO_ACCENT = hsl_to_hex(175, 52, 52)
    TRACK_AUDIO_BODY = hsl_to_hex(175, 48, 36)


# ============================================================================
# ACTIVE THEME SELECTION
# ============================================================================

# Set the active theme here - change to ObsidianGold or ArcticNight to switch
ACTIVE_THEME = MidnightSlate

# Export active theme colors for easy access
BG_DEEPEST = ACTIVE_THEME.BG_DEEPEST
BG_DEEP = ACTIVE_THEME.BG_DEEP
BG_MEDIUM = ACTIVE_THEME.BG_MEDIUM
BG_ELEVATED = ACTIVE_THEME.BG_ELEVATED

ACCENT_PRIMARY = ACTIVE_THEME.ACCENT_PRIMARY
ACCENT_SECONDARY = ACTIVE_THEME.ACCENT_SECONDARY
ACCENT_SUCCESS = ACTIVE_THEME.ACCENT_SUCCESS
ACCENT_WARNING = ACTIVE_THEME.ACCENT_WARNING
ACCENT_ERROR = ACTIVE_THEME.ACCENT_ERROR

BORDER_SUBTLE = ACTIVE_THEME.BORDER_SUBTLE
BORDER_DEFAULT = ACTIVE_THEME.BORDER_DEFAULT
BORDER_STRONG = ACTIVE_THEME.BORDER_STRONG

TEXT_PRIMARY = ACTIVE_THEME.TEXT_PRIMARY
TEXT_SECONDARY = ACTIVE_THEME.TEXT_SECONDARY
TEXT_TERTIARY = ACTIVE_THEME.TEXT_TERTIARY
TEXT_DISABLED = ACTIVE_THEME.TEXT_DISABLED

TRACK_VIDEO_ACCENT = ACTIVE_THEME.TRACK_VIDEO_ACCENT
TRACK_VIDEO_BODY = ACTIVE_THEME.TRACK_VIDEO_BODY
TRACK_AUDIO_ACCENT = ACTIVE_THEME.TRACK_AUDIO_ACCENT
TRACK_AUDIO_BODY = ACTIVE_THEME.TRACK_AUDIO_BODY


# ============================================================================
# SEMANTIC COLOR MAPPINGS
# ============================================================================

# Status Colors
STATUS_PROXY_GENERATING = ACCENT_WARNING
STATUS_PROXY_READY = ACCENT_SUCCESS
STATUS_PROXY_ERROR = ACCENT_ERROR
STATUS_PROXY_INACTIVE = hsl_to_hex(0, 0, 15)  # Near black

# Playhead & Selection
PLAYHEAD_COLOR = hsl_to_hex(0, 0, 100)  # Pure white
SELECTION_BORDER = hsl_to_hex(55, 100, 60)  # Bright yellow

# Waveform Colors
def create_waveform_color():
    """Create semi-transparent waveform color from accent."""
    color = QColor(ACTIVE_THEME.ACCENT_PRIMARY)
    color.setAlpha(180)
    return color

WAVEFORM_COLOR = create_waveform_color()


# ============================================================================
# TYPOGRAPHY SYSTEM
# ============================================================================

FONT_FAMILY_UI = "'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', sans-serif"
FONT_FAMILY_MONO = "'JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Courier New', monospace"

FONT_SIZE_XS = 9
FONT_SIZE_SM = 10
FONT_SIZE_BASE = 11
FONT_SIZE_MD = 12
FONT_SIZE_LG = 14
FONT_SIZE_XL = 16


# ============================================================================
# SPACING SYSTEM (8px base grid)
# ============================================================================

SPACE_XXS = 2
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32


# ============================================================================
# BORDER RADIUS SYSTEM
# ============================================================================

RADIUS_SM = 0
RADIUS_MD = 0
RADIUS_LG = 8
RADIUS_XL = 12

# Semantic Radius Names
RADIUS_CONTAINER = RADIUS_LG  # 8px (Outer Panels)
RADIUS_ELEMENT = 0            # 0px (Internal buttons, tabs, inputs - Square)




# ============================================================================
# SHADOW SYSTEM (for depth)
# ============================================================================

SHADOW_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.3)"
SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)"
SHADOW_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.4)"
SHADOW_XL = "0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 10px 10px -5px rgba(0, 0, 0, 0.5)"


# ============================================================================
# ANIMATION TIMING
# ============================================================================

DURATION_FAST = 150      # ms - Quick interactions
DURATION_NORMAL = 250    # ms - Standard transitions
DURATION_SLOW = 400      # ms - Smooth, noticeable animations

EASING_STANDARD = "cubic-bezier(0.4, 0.0, 0.2, 1)"
EASING_DECELERATE = "cubic-bezier(0.0, 0.0, 0.2, 1)"
EASING_ACCELERATE = "cubic-bezier(0.4, 0.0, 1, 1)"
