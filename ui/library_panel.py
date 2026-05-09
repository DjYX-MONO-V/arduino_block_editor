# ui/library_panel.py
import json
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QAbstractItemView
from PyQt5.QtCore import pyqtSignal, Qt, QMimeData, QSize
from PyQt5.QtGui import QDrag, QIcon

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.library_data = []

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return
        
        row = self.row(item)
        if 0 <= row < len(self.library_data):
            # Упаковываем данные блока в JSON для передачи
            mime = QMimeData()
            mime.setText(json.dumps(self.library_data[row]))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)

class LibraryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Библиотека блоков")
        self.label.setStyleSheet("font-weight: bold; color: #D4D4D4;")
        self.layout.addWidget(self.label)

        self.list_widget = DraggableListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #252526; color: #D4D4D4; border: 1px solid #444; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #094771; }
        """)
        self.list_widget.setIconSize(QSize(150, 100))
        self.layout.addWidget(self.list_widget)

    def update_library(self, data_list):
        self.list_widget.library_data = data_list
        self.list_widget.clear()
        for item in data_list:
            list_item = QListWidgetItem(item.get("name", "Unnamed"))
            
            preview = item.get("_preview_path")
            if preview and os.path.exists(preview):
                list_item.setIcon(QIcon(preview))
            
            list_item.setToolTip(f"{item.get('name')}\n{item.get('description', '')}")
            self.list_widget.addItem(list_item)