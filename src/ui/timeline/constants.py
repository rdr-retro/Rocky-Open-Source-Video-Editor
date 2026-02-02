from PySide6.QtGui import QColor

# Interaction Modes
MODE_IDLE = 0
MODE_MOVE = 1
MODE_TRIM_LEFT = 2
MODE_TRIM_RIGHT = 3
MODE_FADE_IN = 7
MODE_FADE_OUT = 8
MODE_GAIN = 6
MODE_PANNING = 10
MODE_ROLL_EDIT = 4
MODE_RIPPLE_EDIT = 5

# Visual Constants
RESIZE_MARGIN = 10
CLIP_HEADER_HEIGHT = 20
TAG_MARGIN = 15

# Color Palette
BG_COLOR = QColor("#111111")
GRID_COLOR = QColor(255, 255, 255, 80) 
HOVER_CURSOR_COLOR = QColor("#ffffff")

# Clip Themes - EXTREMELY BRIGHT for maximum visibility
THEME_VIDEO = {"header": QColor(220, 100, 120, 255), "body": QColor(180, 80, 100, 255)}
THEME_AUDIO = {"header": QColor(100, 220, 200, 255), "body": QColor(80, 180, 160, 255)}
