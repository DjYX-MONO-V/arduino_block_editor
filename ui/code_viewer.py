# ui/code_viewer.py
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QFrame, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextDocument, QPainter, QTextFormat
from PyQt5.QtCore import QRegExp, Qt, QRect, QSize

class ArduinoSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6")) # VS Code blue
        keywords = ["void", "setup", "loop", "if", "else", "while", "for", "return",
                    "int", "float", "double", "char", "byte", "boolean", "long", "unsigned",
                    "const", "static", "true", "false", "HIGH", "LOW", "INPUT", "OUTPUT", "INPUT_PULLUP"]
        for word in keywords:
            pattern = QRegExp(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Operators
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#D4D4D4")) # White
        operators = ["=", "==", "!=", "<", ">", "<=", ">=", "\\+", "-", "\\*", "/", "%",
                     "&&", "\\|\\|", "!", "&", "\\|", "\\^", "~", "<<", ">>",
                     "\\+=", "-=", "\\*=", "/=", "%="]
        for op in operators:
            pattern = QRegExp(op)
            self.highlighting_rules.append((pattern, operator_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178")) # VS Code orange
        self.highlighting_rules.append((QRegExp("\".*\""), string_format))
        self.highlighting_rules.append((QRegExp("'.*'"), string_format))

        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955")) # VS Code green
        self.highlighting_rules.append((QRegExp("//[^\n]*"), self.comment_format))

        self.comment_start_expression = QRegExp("/\\*")
        self.comment_end_expression = QRegExp("\\*/")

        # Functions (simple detection)
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA")) # VS Code yellow
        self.highlighting_rules.append((QRegExp("\\b[A-Za-z0-9_]+(?=\\()"), function_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8")) # VS Code light green
        self.highlighting_rules.append((QRegExp("\\b[0-9]+\\.?[0-9]*([eE][+-]?[0-9]+)?\\b"), number_format))


    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        # Обработка многострочных комментариев
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = self.comment_start_expression.indexIn(text)

        while start_index >= 0:
            end_index = self.comment_end_expression.indexIn(text, start_index)
            comment_length = 0
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + self.comment_end_expression.matchedLength()

            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = self.comment_start_expression.indexIn(text, start_index + comment_length)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class SearchPanel(QFrame):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setStyleSheet("""
            QFrame { 
                background-color: #252526; 
                border: 1px solid #454545; 
                border-radius: 3px; 
            }
            QLineEdit { 
                background-color: #3C3C3C; 
                color: #D4D4D4; 
                border: 1px solid #555; 
                padding: 2px;
            }
            QPushButton { 
                background-color: #333; 
                color: #D4D4D4; 
                border: 1px solid #454545;
                padding: 1px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #454545; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(3)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Найти...")
        self.search_input.setFixedWidth(120)
        self.search_input.textChanged.connect(self.find_next)
        self.search_input.returnPressed.connect(self.find_next)
        
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setFixedSize(22, 22)
        self.btn_prev.clicked.connect(self.find_prev)
        
        self.btn_next = QPushButton("▼")
        self.btn_next.setFixedSize(22, 22)
        self.btn_next.clicked.connect(self.find_next)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.clicked.connect(self.hide)
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_close)
        
        self.hide()

    def find_next(self):
        text = self.search_input.text()
        if text and not self.editor.find(text):
            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text)

    def find_prev(self):
        text = self.search_input.text()
        if text and not self.editor.find(text, QTextDocument.FindBackward):
            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.End)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, QTextDocument.FindBackward)

    def update_position(self):
        if self.isVisible():
            self.move(self.editor.width() - self.width() - 25, 5)

    def show_and_focus(self):
        self.show()
        self.adjustSize()
        self.update_position()
        self.search_input.setFocus()
        self.search_input.selectAll()


class QCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.searchPanel = SearchPanel(self)
        self.line_numbers_visible = True

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def setLineNumbersVisible(self, visible: bool):
        self.line_numbers_visible = visible
        self.updateLineNumberAreaWidth(0)
        self.lineNumberArea.setVisible(visible)

    def lineNumberAreaWidth(self):
        if not self.line_numbers_visible:
            return 0
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val /= 10
            digits += 1
        space = 15 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
        self.searchPanel.update_position()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.searchPanel.show_and_focus()
            event.accept()
        else:
            super().keyPressEvent(event)

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#2A2D2E")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#2D2D2D")) # Фон области номеров

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#858585")) # Цвет номеров (как в VS Code)
                painter.drawText(0, top, self.lineNumberArea.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1


class CodeViewer(QCodeEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10)) # Моноширинный шрифт для кода
        self.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4;") # Темная тема
        # Для CodeViewer можно убрать подсветку текущей строки, так как он ReadOnly
        self.cursorPositionChanged.disconnect(self.highlightCurrentLine)
        
        self.highlighter = ArduinoSyntaxHighlighter(self.document())

    def set_code(self, code: str):
        self.setPlainText(code)
