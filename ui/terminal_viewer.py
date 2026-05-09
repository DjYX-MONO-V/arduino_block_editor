# ui/terminal_viewer.py
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont, QColor

class TerminalViewer(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9)) # Моноширинный шрифт для вывода терминала
        self.setStyleSheet("""
            background-color: #000000; /* Черный фон */
            color: #00FF00; /* Зеленый текст */
            border: 1px solid #444444;
            padding: 5px;
        """)
        self.setText("Терминал готов.")

    def append_output(self, text: str, color: str = "#00FF00"):
        """Добавляет текст в терминал с указанным цветом."""
        self.setTextColor(QColor(color))
        self.append(text)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()) # Автопрокрутка вниз

    def clear_output(self):
        self.clear()