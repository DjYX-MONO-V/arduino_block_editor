# ui/block_widgets.py
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsProxyWidget, QTextEdit, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QColorDialog, QMenu, QGraphicsItem, QSplitter
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject, QPointF
from PyQt5.QtGui import QBrush, QPen, QColor, QFont
from core.block_data_models import FunctionBlockData
from ui.code_viewer import ArduinoSyntaxHighlighter, QCodeEditor

class BlockSignals(QObject):
    """Вспомогательный класс для передачи сигналов от графических элементов"""
    block_data_changed = pyqtSignal()
    request_deletion = pyqtSignal(object) # Передает сам виджет для удаления
    request_library_save = pyqtSignal(object) # Передает данные блока для сохранения

class ResizeHandle(QGraphicsRectItem):
    """Небольшой квадрат в углу блока для изменения размера"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setRect(-10, -10, 10, 10)
        self.setBrush(QBrush(QColor("#007ACC")))
        self.setCursor(Qt.SizeFDiagCursor)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        parent = self.parentItem()
        if parent:
            new_w = max(200, self.pos().x())
            new_h = max(100, self.pos().y())
            parent.resize_block(new_w, new_h)

class FunctionBlockWidget(QGraphicsRectItem):
    def __init__(self, block_data: FunctionBlockData, parent=None):
        super().__init__(parent)
        self.signals = BlockSignals() # Используем объект сигналов
        self.block_data = block_data
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges)

        self.is_minimized = False

        self.setRect(0, 0, self.block_data.width, self.block_data.height)
        self.setBrush(QBrush(QColor(self.block_data.color))) # Цвет фона блока
        self.setPen(QPen(QColor("#007ACC"), 2)) # Цвет рамки

        self._create_widgets()
        self._update_ui_from_data()

    def _create_widgets(self):
        # Кнопки управления
        self.min_btn = QPushButton("_")
        self.min_btn.setFixedSize(20, 20)
        self.min_btn.setStyleSheet("background-color: #555; color: white; border: none; font-weight: bold; padding: 0px;")
        self.min_btn.clicked.connect(self._toggle_minimize)

        self.del_btn = QPushButton("X")
        self.del_btn.setFixedSize(20, 20)
        self.del_btn.setStyleSheet("background-color: #A33; color: white; border: none; font-weight: bold; padding: 0px;")
        self.del_btn.clicked.connect(self._request_delete)

        # Кнопка выбора цвета
        self.color_btn = QPushButton("🎨")
        self.color_btn.setFixedSize(20, 20)
        self.color_btn.setStyleSheet("background-color: #555; color: white; border: none; font-size: 12px; padding: 0px;")
        self.color_btn.clicked.connect(self._change_color)

        # Заголовок блока (имя функции)
        self.name_label = QLineEdit(self.block_data.name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        # Начальный стиль для name_label, будет обновлен _update_ui_from_data
        self.name_label.setStyleSheet(f"background-color: {self.block_data.color}; color: #D4D4D4; border: none; padding: 2px;")
        self.name_label.textChanged.connect(self._on_name_changed)

        self.save_btn = QPushButton("💾")
        self.save_btn.setFixedSize(20, 20)
        self.save_btn.setStyleSheet("background-color: #555; color: white; border: none; font-size: 12px; padding: 0px;")
        self.save_btn.setToolTip("Сохранить в библиотеку")
        self.save_btn.clicked.connect(self._save_to_library)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.name_label)
        header_layout.addWidget(self.color_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.min_btn)
        header_layout.addWidget(self.del_btn)

        # Описание функции
        self.description_editor = QTextEdit(self.block_data.description)
        self.description_editor.setPlaceholderText("Описание функции...")
        # Начальный стиль для description_editor, будет обновлен _update_ui_from_data
        self.description_editor.setStyleSheet(f"background-color: {self.block_data.color}; color: #D4D4D4; border: 1px solid #555; padding: 2px;")
        self.description_editor.textChanged.connect(self._on_description_changed)

        # Редактор кода с нумерацией строк
        self.code_editor = QCodeEditor()
        self.code_editor.setPlainText(self.block_data.code_content)
        self.code_editor.setFont(QFont("Consolas", 9))
        self.code_editor.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4; border: 1px solid #555; padding: 2px;")
        self.code_editor.textChanged.connect(self._on_code_changed)

        # Применяем подсветку синтаксиса к редактору кода в блоке
        self.code_highlighter = ArduinoSyntaxHighlighter(self.code_editor.document())

        # Создаем разделитель (Splitter) для управления размерами окон внутри блока
        self.editor_splitter = QSplitter(Qt.Vertical)
        self.editor_splitter.addWidget(self.description_editor)
        self.editor_splitter.addWidget(self.code_editor)
        # Устанавливаем начальное распределение места (1/4 для описания, 3/4 для кода)
        self.editor_splitter.setStretchFactor(0, 1)
        self.editor_splitter.setStretchFactor(1, 3)
        self.editor_splitter.setHandleWidth(2)
        self.editor_splitter.setStyleSheet("QSplitter::handle { background-color: #555; }")

        # Создаем виджет-контейнер для размещения элементов
        container_widget = QWidget()
        # Устанавливаем начальный фон для контейнера
        container_widget.setStyleSheet(f"background-color: {self.block_data.color};")
        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addLayout(header_layout)
        layout.addWidget(self.editor_splitter)

        # Встраиваем виджет-контейнер в QGraphicsScene
        self.proxy_widget = QGraphicsProxyWidget(self)
        self.proxy_widget.setWidget(container_widget)
        self.proxy_widget.setPos(0, 0) # Позиция внутри QGraphicsRectItem

        # Добавляем манипулятор изменения размера
        self.resize_handle = ResizeHandle(self)

        # Обновляем размер QGraphicsRectItem, чтобы он соответствовал содержимому
        self.update_size()

    def _update_ui_from_data(self):
        self.name_label.setText(self.block_data.name)
        self.description_editor.setText(self.block_data.description)
        self.code_editor.setPlainText(self.block_data.code_content)
        self.setPos(self.block_data.pos_x, self.block_data.pos_y)
        self.setBrush(QBrush(QColor(self.block_data.color))) # Обновляем кисть QGraphicsRectItem
        self.proxy_widget.widget().setStyleSheet(f"background-color: {self.block_data.color};") # Обновляем фон контейнера
        self.name_label.setStyleSheet(f"background-color: {self.block_data.color}; color: #D4D4D4; border: none; padding: 2px;") # Обновляем фон name_label
        self.description_editor.setStyleSheet(f"background-color: {self.block_data.color}; color: #D4D4D4; border: 1px solid #555; padding: 2px;") # Обновляем фон description_editor
        self.update_size()

    def _on_name_changed(self):
        self.block_data.name = self.name_label.text()
        self.signals.block_data_changed.emit()

    def _on_description_changed(self):
        self.block_data.description = self.description_editor.toPlainText()
        self.signals.block_data_changed.emit()

    def _on_code_changed(self):
        self.block_data.code_content = self.code_editor.toPlainText()
        self.signals.block_data_changed.emit()

    def _toggle_minimize(self):
        self.is_minimized = not self.is_minimized
        self.description_editor.setVisible(not self.is_minimized)
        self.code_editor.setVisible(not self.is_minimized)
        self.min_btn.setText("□" if self.is_minimized else "_")
        self.update_size()

    def _request_delete(self):
        reply = QMessageBox.question(None, "Удаление", f"Удалить блок '{self.block_data.name}'?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.signals.request_deletion.emit(self)

    def _save_to_library(self):
        self.signals.request_library_save.emit(self)

    def resize_block(self, width, height):
        self.block_data.width = width
        self.block_data.height = height
        self.update_size(update_handle=False)
        self.signals.block_data_changed.emit()

    def contextMenuEvent(self, event):
        menu = QMenu()
        color_action = menu.addAction("Изменить цвет")
        action = menu.exec_(event.screenPos())
        if action == color_action:
            self._change_color()

    def _change_color(self):
        color = QColorDialog.getColor(QColor(self.block_data.color))
        if color.isValid():
            self.block_data.color = color.name()
            self.setBrush(QBrush(color)) # Обновляем кисть QGraphicsRectItem
            # Обновляем фон виджетов внутри блока
            self.proxy_widget.widget().setStyleSheet(f"background-color: {color.name()};")
            self.name_label.setStyleSheet(f"background-color: {color.name()}; color: #D4D4D4; border: none; padding: 2px;")
            self.description_editor.setStyleSheet(f"background-color: {color.name()}; color: #D4D4D4; border: 1px solid #555; padding: 2px;")
            self.signals.block_data_changed.emit()

    def update_size(self, update_handle=True): # Метод update_size остался без изменений, так как он был корректен
        width = self.block_data.width
        
        if self.is_minimized:
            height = self.name_label.sizeHint().height() + 15
        else:
            height = self.block_data.height
                     
        self.setRect(0, 0, width, height)
        self.proxy_widget.setGeometry(QRectF(0, 0, width, height))
        if update_handle:
            self.resize_handle.setPos(width, height)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged:
            # Обновляем данные о позиции при перемещении блока
            self.block_data.pos_x = value.x()
            self.block_data.pos_y = value.y()
            self.signals.block_data_changed.emit() # Оповещаем об изменении
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        # Пример: при двойном клике можно открыть блок для более детального редактирования
        QMessageBox.information(None, "Редактирование блока", f"Двойной клик по блоку: {self.block_data.name}")
        super().mouseDoubleClickEvent(event)
