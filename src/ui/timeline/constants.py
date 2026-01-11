from PyQt5.QtGui import QColor

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

# Clip Themes (Refined Maroon & Professional Teal - desaturated aesthetic)
THEME_VIDEO = {"header": QColor(158, 54, 74, 200), "body": QColor(125, 42, 58, 160)}
THEME_AUDIO = {"header": QColor(54, 158, 147, 200), "body": QColor(42, 125, 117, 160)}
