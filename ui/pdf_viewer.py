# ui/pdf_viewer.py
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QSplitter, QLabel, QFrame, QLineEdit, QPushButton, QSizePolicy, QApplication
from PyQt5.QtCore import Qt, QUrl, QRect, QTimer, QEvent
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
except ImportError:
    # Заглушка, если библиотека не установлена
    QWebEngineView = None

class PDFSearchPanel(QFrame):
    def __init__(self, webview, parent=None):
        super().__init__(parent)
        self.webview = webview
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.last_search = "" # Храним последний успешный запрос

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
        self.search_input.setPlaceholderText("Найти в PDF...")
        self.search_input.setFixedWidth(150)
        
        # Таймер для задержки поиска (чтобы не спамить запросами при каждом нажатии клавиши)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_search)
        
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._do_search)
        
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

    def _on_text_changed(self):
        """Запускается при каждом изменении текста, но ждет 500мс перед поиском."""
        self.search_timer.stop()
        self.search_timer.start(500) # Задержка в полсекунды

    def _do_search(self):
        """Выполняет фактический поиск."""
        # Не ищем, если документ еще не готов
        if not self.parent().is_document_loaded:
            return

        text = self.search_input.text()
        if text == self.last_search: # Не спамим, если текст не изменился
            return
            
        if len(text) > 1: # Ищем только если введено более 1 символа
            self.webview.findText(text)
            self.last_search = text
        elif not text:
            self.webview.findText("")
            self.last_search = ""

    def find_next(self):
        self._do_search()

    def find_prev(self):
        text = self.search_input.text()
        if not self.parent().is_document_loaded:
            return
        if text.strip():
            # FindBackward — самый стабильный флаг для всех версий PyQt5
            self.webview.findText(text, QWebEnginePage.FindBackward)

    def show_and_focus(self):
        self.adjustSize() # Пересчитываем размер перед показом
        self.show()
        self.raise_()    # Выводим на передний план над WebView
        self.search_input.setFocus()
        self.search_input.selectAll()

class PDFViewerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Документация и учебные материалы")
        self.resize(1000, 700)
        self.setModal(False)

        self.is_document_loaded = False # Флаг готовности документа
        
        self.main_window = parent
        self._init_ui()
        self._load_file_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        if QWebEngineView is None:
            error_label = QLabel("Для просмотра PDF установите библиотеку:\npip install PyQtWebEngine")
            error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return

        self.splitter = QSplitter(Qt.Horizontal)
        
        # Список файлов
        self.file_list = QListWidget()
        self.file_list.setMaximumWidth(250)
        self.file_list.setStyleSheet("""
            QListWidget { background-color: #252526; color: #D4D4D4; border: 1px solid #454545; }
            QListWidget::item:selected { background-color: #094771; }
        """)
        self.file_list.itemClicked.connect(self._on_file_selected)
        
        # Просмотрщик (Браузер)
        self.webview = QWebEngineView()
        self.webview.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self.webview.settings().setAttribute(QWebEngineSettings.PdfViewerEnabled, True)
        self.webview.loadFinished.connect(self._on_load_finished)
        
        self.splitter.addWidget(self.file_list)
        self.splitter.addWidget(self.webview)
        
        layout.addWidget(self.splitter)

        # Создаем панель поиска ПОСЛЕ того, как WebView добавлен в компоновку,
        # чтобы панель была выше в иерархии отрисовки.
        self.search_panel = PDFSearchPanel(self.webview, self)

    def _on_load_finished(self, ok):
        """Вызывается, когда PDF полностью загружен в WebView."""
        if ok:
            # Даже после loadFinished PDF-плагину нужно время на инициализацию JS.
            # Даем ему 500мс, прежде чем разрешить поиск.
            QTimer.singleShot(500, self._set_document_ready)
        else:
            self.is_document_loaded = False

    def _set_document_ready(self):
        self.is_document_loaded = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_search_panel_position()

    def _update_search_panel_position(self):
        """Обновляет позицию панели поиска и удерживает её на переднем плане."""
        if self.search_panel.isVisible():
            self.search_panel.adjustSize() # Гарантируем актуальную ширину
            # Смещаем чуть левее от края, чтобы панель не обрезалась
            self.search_panel.move(self.width() - self.search_panel.width() - 30, 10)
            self.search_panel.raise_() # Принудительно поднимаем над WebView

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.search_panel.show_and_focus()
            self._update_search_panel_position() # Обновляем позицию после показа
            event.accept()
        else:
            super().keyPressEvent(event)

    def _load_file_list(self):
        if QWebEngineView is None: return
        
        self.file_list.clear()
        # Получаем путь из настроек через MainWindow
        doc_path = self.main_window.settings_manager.get_setting("pdf_docs_path")
        
        if not doc_path or not os.path.exists(doc_path):
            self.file_list.addItem("Папка не найдена. Проверьте настройки.")
            return

        files = [f for f in os.listdir(doc_path) if f.lower().endswith('.pdf')]
        if not files:
            self.file_list.addItem("PDF файлы не найдены.")
            return

        for file_name in sorted(files):
            item = QListWidgetItem(file_name)
            item.setData(Qt.UserRole, os.path.join(doc_path, file_name))
            self.file_list.addItem(item)

    def _on_file_selected(self, item):
        file_path = item.data(Qt.UserRole)
        self.is_document_loaded = False # Сбрасываем флаг при смене файла
        if file_path and os.path.exists(file_path):
            # QWebEngineView открывает PDF через URL
            file_url = QUrl.fromLocalFile(file_path)
            self.webview.load(file_url)