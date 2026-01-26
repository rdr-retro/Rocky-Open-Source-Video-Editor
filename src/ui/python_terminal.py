import sys
import io
import traceback
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

class ConsoleEditor(QPlainTextEdit):
    """Subclass to handle terminal-specific keyboard events."""
    execute_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompt = ">>> "

    def keyPressEvent(self, event):
        # Prevent user from deleting the prompt or moving back into history
        # (Very basic protection for now)
        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            if cursor.positionInBlock() <= len(self.prompt):
                return

        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if not (event.modifiers() & Qt.ShiftModifier):
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                line = cursor.selectedText()
                self.execute_requested.emit(line)
                return
        
        super().keyPressEvent(event)

class PythonTerminalPanel(QWidget):
    """
    An interactive Python terminal integrated as a Rocky Panel.
    Allows executing commands and inspecting the application state.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PythonTerminal")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.editor = ConsoleEditor()
        self.editor.setReadOnly(False)
        self.editor.execute_requested.connect(self.execute_command)
        
        # Professional Console Styling
        font = QFont("JetBrains Mono", 10)
        if not font.fixedPitch():
            font = QFont("Courier New", 10)
        self.editor.setFont(font)
        
        from . import styles as s
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #0d0d0d;
                color: #00ff44;
                border: none;
                selection-background-color: #2f4f4f;
            }}
            {s.SCROLLBAR_STYLE}
        """)
        
        layout.addWidget(self.editor)
        
        self.intro_text = "Rocky Video Editor - Python Terminal\nType commands below. 'app' and 'model' are available.\n"
        self.editor.setPlainText(self.intro_text + ">>> ")
        self.move_cursor_to_end()
        
        # Ensure focus
        self.editor.setFocus()
        
        self.locals = {}
        
    def move_cursor_to_end(self):
        self.editor.moveCursor(QTextCursor.End)

    def execute_command(self, line):
        # Strip the prompt if present
        if line.startswith(">>> "):
            cmd = line[4:].strip()
        else:
            cmd = line.strip()
            
        if not cmd:
            self.editor.appendPlainText(">>> ")
            self.move_cursor_to_end()
            return

        # Inject context
        from PySide6.QtWidgets import QApplication
        app_inst = QApplication.instance()
        for widget in app_inst.topLevelWidgets():
            if hasattr(widget, "model"):
                self.locals["app"] = widget
                self.locals["model"] = widget.model
                break

        # Execution
        self.editor.appendPlainText("") 
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        sys.stderr = redirected_output
        
        try:
            try:
                result = eval(cmd, globals(), self.locals)
                if result is not None:
                    print(repr(result))
            except:
                exec(cmd, globals(), self.locals)
        except Exception:
            dest = io.StringIO()
            traceback.print_exc(file=dest)
            print(dest.getvalue())
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
        output = redirected_output.getvalue()
        if output:
            self.editor.appendPlainText(output.strip())
            
        self.editor.appendPlainText(">>> ")
        self.move_cursor_to_end()

    def update_context(self, selection):
        self.locals['selection'] = selection
