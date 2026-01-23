"""
Rocky Video Editor - Global Style Definitions
Organized hierarchy of QSS styles leveraging design tokens for theme consistency.
"""

from . import design_tokens as dt

# ============================================================================
# 1. CORE COMPONENT BACKGROUNDS
# ============================================================================

WORKSPACE_BG = dt.BG_DEEPEST
PANEL_BG = dt.BG_DEEP
TIMECODE_HEADER_BG = dt.BG_MEDIUM
MODERN_LABEL = f"""
    color: {dt.TEXT_PRIMARY};
    font-family: {dt.FONT_FAMILY_UI};
    font-size: {dt.FONT_SIZE_BASE}px;
"""

# ============================================================================
# 2. TIMELINE & TRACKS
# ============================================================================

TRACK_VIDEO_SIDEBAR = dt.BG_ELEVATED
TRACK_AUDIO_SIDEBAR = dt.BG_DEEPEST

STRIP_VIDEO = dt.TRACK_VIDEO_ACCENT
STRIP_AUDIO = dt.TRACK_AUDIO_ACCENT

CLIP_VIDEO_HEADER = dt.TRACK_VIDEO_ACCENT
CLIP_VIDEO_BODY = dt.TRACK_VIDEO_BODY
CLIP_AUDIO_HEADER = dt.TRACK_AUDIO_ACCENT
CLIP_AUDIO_BODY = dt.TRACK_AUDIO_BODY

# ============================================================================
# 3. TYPOGRAPHY & SHARED TOKENS
# ============================================================================

UI_FONT = dt.FONT_FAMILY_UI
MONO_FONT = dt.FONT_FAMILY_MONO
ACCENT_PRIMARY = dt.ACCENT_PRIMARY

# ============================================================================
# 4. QSS STYLE BLOCKS
# ============================================================================

# --- TOOLBAR & MENUS ---

TOOLBAR_STYLE = f"""
    QFrame#Toolbar {{
        background-color: transparent;
        border: none;
    }}
"""

TOOLBAR_MENU_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {dt.TEXT_SECONDARY};
        border: none;
        padding: 0px 8px;
        min-height: 24px;
        max-height: 24px;
        font-family: {dt.FONT_FAMILY_UI};
        font-size: 11px;
        text-align: center;
        outline: none;
        border-radius: 6px;
    }}
    QPushButton:hover {{
        background-color: {dt.BG_ELEVATED};
        color: {dt.TEXT_PRIMARY};
    }}
    QPushButton::menu-indicator {{
        image: none;
    }}
"""

WORKSPACE_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {dt.TEXT_SECONDARY};
        border: none;
        padding: 0px 10px;
        min-height: 24px;
        max-height: 24px;
        font-family: {dt.FONT_FAMILY_UI};
        font-size: 11px;
        text-align: center;
        outline: none;
        border-radius: 6px;
    }}
    QPushButton:hover {{
        background-color: {dt.BG_MEDIUM};
        color: {dt.TEXT_PRIMARY};
    }}
    QPushButton:checked {{
        background-color: {dt.BG_ELEVATED};
        color: {dt.TEXT_PRIMARY};
        font-weight: 500;
        border: 1px solid {dt.BORDER_SUBTLE};
    }}
"""

MENU_STYLE = f"""
    QMenu {{
        background-color: {dt.BG_DEEP};
        border: 1px solid {dt.BORDER_DEFAULT};
        color: {dt.TEXT_PRIMARY};
        font-family: {dt.FONT_FAMILY_UI};
        font-size: {dt.FONT_SIZE_BASE}px;
        border-radius: {dt.RADIUS_CONTAINER}px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 4px 24px 4px 12px;
        background-color: transparent;
        border-radius: {dt.RADIUS_ELEMENT}px;
        margin: 1px;
    }}
    QMenu::item:selected {{
        background-color: {dt.ACCENT_PRIMARY};
        color: {dt.BG_DEEPEST};
    }}
    QMenu::separator {{
        height: 1px;
        background: {dt.BORDER_DEFAULT};
        margin: 4px 8px;
    }}
"""

# --- COMMON BUTTONS ---

PUSH_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {dt.BG_MEDIUM};
        color: {dt.TEXT_PRIMARY};
        border: 1px solid {dt.BORDER_SUBTLE};
        padding: 3px 8px;
        font-family: {dt.FONT_FAMILY_UI};
        font-size: {dt.FONT_SIZE_SM}px;
    }}
    QPushButton:hover {{
        background-color: {dt.BG_ELEVATED};
    }}
    QPushButton:pressed {{
        background-color: {dt.BG_DEEP};
    }}
    QPushButton:checked {{
        background-color: {dt.ACCENT_PRIMARY};
        color: {dt.BG_DEEPEST};
        font-weight: bold;
    }}
"""

# --- FORM ELEMENTS ---

SLIDER_STYLE = f"""
    QSlider {{
        background: transparent;
    }}
    QSlider::groove:horizontal {{
        border: 1px solid {dt.BORDER_DEFAULT};
        height: 3px;
        background: {dt.BG_DEEPEST};
    }}
    QSlider::handle:horizontal {{
        background: {dt.TEXT_PRIMARY};
        border: 1px solid {dt.BORDER_STRONG};
        width: 8px;
        height: 12px;
        margin: -5px 0;
    }}
"""
# --- SCROLLBARS (MINIMALIST PILL STYLE) ---

SCROLLBAR_STYLE = f"""
    QScrollBar:horizontal {{
        border: none;
        background: transparent;
        height: 14px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: #444;
        min-width: 30px;
        border-radius: 5px;
        border: 1px solid transparent; /* Forced clipping for macOS */
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #ffffff;
        border-radius: 5px;
        border: 1px solid transparent;
    }}

    /* Vertical ScrollBar */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 14px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #444;
        min-height: 30px;
        border-radius: 5px;
        border: 1px solid transparent; /* Forced clipping for macOS */
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #ffffff;
        border-radius: 5px;
        border: 1px solid transparent;
    }}
    
    /* Background elements */
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
        width: 0px;
        height: 0px;
    }}
    
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QAbstractScrollArea::corner {{
        background: transparent;
        border: none;
    }}
"""
