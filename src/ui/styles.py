# Rocky Video Editor - Dynamic Styles using Design Tokens
# This file now imports colors from design_tokens.py for theme support

from . import design_tokens as dt

# ============================================================================
# BACKGROUND COLORS (from active theme)
# ============================================================================
WORKSPACE_BG = dt.BG_DEEPEST
PANEL_BG = dt.BG_DEEP
TIMECODE_HEADER_BG = dt.BG_MEDIUM

# ============================================================================
# TRACK COLORS (from active theme)
# ============================================================================
TRACK_VIDEO_SIDEBAR = dt.BG_ELEVATED
TRACK_AUDIO_SIDEBAR = dt.BG_DEEPEST

STRIP_VIDEO = dt.TRACK_VIDEO_ACCENT
STRIP_AUDIO = dt.TRACK_AUDIO_ACCENT

# ============================================================================
# CLIP COLORS (from active theme)
# ============================================================================
CLIP_VIDEO_HEADER = dt.TRACK_VIDEO_ACCENT
CLIP_VIDEO_BODY = dt.TRACK_VIDEO_BODY
CLIP_AUDIO_HEADER = dt.TRACK_AUDIO_ACCENT
CLIP_AUDIO_BODY = dt.TRACK_AUDIO_BODY

# ============================================================================
# ACCENT & TEXT COLORS (from active theme)
# ============================================================================
ACCENT_BLUE = dt.ACCENT_PRIMARY
ACCENT_PRIMARY = dt.ACCENT_PRIMARY
TEXT_WHITE = dt.TEXT_PRIMARY
TEXT_SUBTLE = dt.TEXT_SECONDARY

# ============================================================================
# TYPOGRAPHY (from design tokens)
# ============================================================================
UI_FONT = dt.FONT_FAMILY_UI
MONO_FONT = dt.FONT_FAMILY_MONO

# ============================================================================
# QSS STYLES (using design tokens)
# ============================================================================

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

TOOLBAR_STYLE = f"""
QFrame#Toolbar {{
    background-color: {dt.BG_DEEP};
    border-bottom: 1px solid {dt.BORDER_SUBTLE};
}}
"""

TOOLBAR_MENU_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: #ffffff;
    border: none;
    padding: 2px 8px;
    font-family: {dt.FONT_FAMILY_UI};
    font-size: 11px;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
}}
QPushButton::menu-indicator {{
    image: none;
}}
"""

WORKSPACE_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: #ffffff;
    border: none;
    padding: 2px 8px;
    font-family: {dt.FONT_FAMILY_UI};
    font-size: 11px;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
}}
QPushButton:checked {{
    background-color: transparent;
    color: {dt.ACCENT_PRIMARY};
    font-weight: bold;
}}
"""

MODERN_LABEL = f"""
color: {dt.TEXT_PRIMARY};
font-family: {dt.FONT_FAMILY_UI};
font-size: {dt.FONT_SIZE_BASE}px;
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
