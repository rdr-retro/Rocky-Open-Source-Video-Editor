# Exact UI Design System from Image
# Replicating the provided reference image colors

# Backgrounds
WORKSPACE_BG = "#333333"  # General timeline / workspace background
PANEL_BG = "#252525"      # Secondary panels
TIMECODE_HEADER_BG = "#282828" # The specific dark grey for timecode

# Track Sidebar Special Colors
TRACK_VIDEO_SIDEBAR = "#748a91" # Light blue-grey for video track info
TRACK_AUDIO_SIDEBAR = "#333333" # Dark grey for audio track info

# Strip Colors (The vertical color line)
STRIP_VIDEO = "#7b3145" # Dark maroon
STRIP_AUDIO = "#4f6a96" # Steel blue

# Clip Themes
CLIP_VIDEO_HEADER = "#7b3145" # Maroon header
CLIP_VIDEO_BODY = "#632738"   # Slightly darker body
CLIP_AUDIO_HEADER = "#4f6a96" # Blue header
CLIP_AUDIO_BODY = "#3a4d6e"   # Slightly darker body

# Accents
ACCENT_BLUE = "#00a3ff"       # The blue for small icons/selection
TEXT_WHITE = "#ffffff"
TEXT_SUBTLE = "#cccccc"

# Typography
UI_FONT = "'Inter', '.AppleSystemUIFont', 'Helvetica Neue', sans-serif"
MONO_FONT = "'Menlo', 'Monaco', 'Courier New', monospace"

SLIDER_STYLE = f"""
QSlider {{
    background: transparent;
}}
QSlider::groove:horizontal {{
    border: 1px solid #444444;
    height: 3px;
    background: #111111;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 1px solid #000000;
    width: 8px;
    height: 12px;
    margin: -5px 0;
}}
"""

PUSH_BUTTON_STYLE = f"""
QPushButton {{
    background-color: #444444;
    color: #ffffff;
    border: 1px solid #222222;
    padding: 3px 8px;
    font-family: {UI_FONT};
    font-size: 10px;
}}
QPushButton:hover {{
    background-color: #555555;
}}
QPushButton:pressed {{
    background-color: #222222;
}}
QPushButton:checked {{
    background-color: #00a3ff;
    color: #000000;
    font-weight: bold;
}}
"""

TOOLBAR_STYLE = f"""
QFrame#Toolbar {{
    background-color: #333333;
    border-bottom: 1px solid #000000;
}}
"""

MODERN_LABEL = f"""
color: #ffffff;
font-family: {UI_FONT};
font-size: 11px;
"""

MENU_STYLE = f"""
QMenu {{
    background-color: #333333; /* Dark background */
    border: 1px solid #000000;
    color: #ffffff;
    font-family: {UI_FONT};
    font-size: 11px;
    border-radius: 6px; /* Rounded corners */
    padding: 4px; /* Padding for the rounding */
}}
QMenu::item {{
    padding: 4px 24px 4px 12px;
    background-color: transparent;
    border-radius: 4px; /* Rounded selection matches menu */
    margin: 1px; /* Spacing between items */
}}
QMenu::item:selected {{
    background-color: {ACCENT_BLUE}; /* High contrast blue */
    color: #000000; /* Dark text for contrast against bright blue */
}}
QMenu::separator {{
    height: 1px;
    background: #555555;
    margin: 4px 8px; /* Indented separator */
}}
"""
