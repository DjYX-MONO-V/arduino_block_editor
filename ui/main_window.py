# ui/main_window.py
import os
import json
import subprocess
import tempfile
import shutil
import zipfile
import re
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
                             QAction, QMessageBox, QFileDialog, QDockWidget, QDialog, QPushButton, 
                             QComboBox, QLabel, QApplication, QLineEdit, QInputDialog)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QSize, QPointF, QTimer
from ui.block_canvas import BlockCanvas
from ui.code_viewer import CodeViewer
from ui.library_panel import LibraryPanel
from ui.settings_dialog import SettingsDialog
from core.settings_manager import SettingsManager
from core.code_generator import generate_arduino_code
from ui.terminal_viewer import TerminalViewer
from ui.calculator_window import CalculatorWindow # Импортируем новый класс калькулятора
from ui.pdf_viewer import PDFViewerWindow # Импортируем новое окно PDF
from core.block_data_models import BlockProject, FunctionBlockData

# Определяем путь к корню проекта (на уровень выше от папки ui)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arduino Block Editor")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        self.calculator_window = None # Ссылка на окно калькулятора
        self.pdf_viewer_window = None # Ссылка на окно PDF
        self.serial_monitor = None # Ссылка на окно монитора

        self.current_project = BlockProject() # Текущий проект блоков
        self.settings_manager = SettingsManager()
        
        self.statusBar().showMessage("Готово")

        self.library_dir = self.settings_manager.get_setting("library_path", os.path.join(os.path.expanduser("~"), "ArduinoBlockLibrary"))
        self.saved_library = self._load_library()
        
        self.available_boards = [] # Список доступных плат
        self._current_board_config_options = {} # {option_key: selected_value_key}
        self._cli_executable_path = None # Кэш пути к arduino-cli

        self._apply_dark_theme()
        self._create_main_layout()
        self._create_toolbar()
        self._create_menu_bar()
        
        # Заполняем списки плат и портов только после того, как создано меню "Инструменты",
        # чтобы избежать ошибки AttributeError при попытке обновить пункты меню.
        self.populate_board_selector()
        self.populate_port_selector()
        
        # Инициализируем меню примеров
        self._update_examples_menu()

        # При первом запуске или если проект пуст, добавляем стандартные блоки
        if not self.current_project.function_blocks:
            self.block_canvas.add_default_blocks()

    def _apply_dark_theme(self):
        """Применяет современную темную тему оформления ко всему приложению."""
        dark_stylesheet = """
            QMainWindow, QDialog, QDockWidget {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            QWidget {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            QMenuBar {
                background-color: #333333;
                color: #D4D4D4;
                border-bottom: 1px solid #2D2D2D;
            }
            QMenuBar::item:selected {
                background-color: #454545;
            }
            QMenu {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #454545;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QDockWidget::title {
                background-color: #2D2D2D;
                padding: 6px;
                border-bottom: 1px solid #3F3F3F;
            }
            QSplitter::handle {
                background-color: #2D2D2D;
            }
            QToolBar {
                background-color: #333333;
                border-bottom: 1px solid #2D2D2D;
                spacing: 8px;
            }
            QPushButton {
                background-color: #333333;
                color: #D4D4D4;
                border: 1px solid #454545;
                padding: 4px 8px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #454545;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
            QPushButton:disabled {
                background-color: #252526;
                color: #666666;
            }
            QComboBox {
                background-color: #3C3C3C;
                color: #D4D4D4;
                border: 1px solid #454545;
                padding: 2px 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #D4D4D4;
                selection-background-color: #094771;
                border: 1px solid #454545;
            }
            QLineEdit, QTextEdit {
                background-color: #3C3C3C;
                color: #D4D4D4;
                border: 1px solid #454545;
                selection-background-color: #264F78;
            }
            QLabel {
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #1E1E1E;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4F4F4F;
            }
            QScrollBar:horizontal {
                border: none;
                background: #1E1E1E;
                height: 10px;
            }
            QScrollBar::handle:horizontal {
                background: #424242;
                min-width: 20px;
            }
        """
        QApplication.instance().setStyleSheet(dark_stylesheet)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("Файл")

        new_action = QAction("Новый проект", self)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("Открыть проект...", self)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить проект...", self)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        self.examples_menu = file_menu.addMenu("Примеры")
        # Меню примеров будет заполняться динамически

        export_bundle_action = QAction("Экспортировать проект с библиотеками...", self)
        export_bundle_action.triggered.connect(self._export_project_bundle)
        file_menu.addAction(export_bundle_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню "Настройки"
        settings_menu = menu_bar.addMenu("Настройки")
        settings_action = QAction("Настройки программы...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

        # Меню "Инструменты"
        self.tools_menu = menu_bar.addMenu("Инструменты")
        
        autoformat_action = QAction("АвтоФорматирование", self)
        autoformat_action.setShortcut("Ctrl+T")
        autoformat_action.triggered.connect(self._auto_format_code)
        self.tools_menu.addAction(autoformat_action)
        
        archive_action = QAction("Архивировать скетч", self)
        archive_action.triggered.connect(self._archive_project)
        self.tools_menu.addAction(archive_action)
        
        manage_libs_action = QAction("Управление библиотеками...", self)
        manage_libs_action.setShortcut("Ctrl+Shift+I")
        manage_libs_action.triggered.connect(self._open_settings) # Открывает настройки, где есть вкладка библиотек
        self.tools_menu.addAction(manage_libs_action)
        
        serial_monitor_action = QAction("Монитор порта", self)
        serial_monitor_action.setShortcut("Ctrl+Shift+M")
        serial_monitor_action.triggered.connect(self._open_serial_monitor)
        self.tools_menu.addAction(serial_monitor_action)
        
        calculator_action = QAction("Калькулятор", self)
        calculator_action.triggered.connect(self._open_calculator)
        self.tools_menu.addAction(calculator_action)

        pdf_viewer_action = QAction("Документация (PDF)", self)
        pdf_viewer_action.triggered.connect(self._open_pdf_viewer)
        self.tools_menu.addAction(pdf_viewer_action)

        self.tools_menu.addSeparator()

        # Динамические меню для платы и порта
        self.board_menu = self.tools_menu.addMenu("Плата: Не выбрана")
        self.port_menu = self.tools_menu.addMenu("Порт: Не выбран")
        self.processor_menu = self.tools_menu.addMenu("Процессор: Не выбран") # Kept for 'cpu' option
        self.board_options_menu = self.tools_menu.addMenu("Параметры платы")
        self.board_options_menu.setEnabled(False) # Initially disabled

        self.tools_menu.addSeparator()
        
        get_board_info_action = QAction("Получить информацию о подключенной плате", self)
        get_board_info_action.triggered.connect(self._get_board_info)
        self.tools_menu.addAction(get_board_info_action)

        self.tools_menu.addSeparator()
        burn_bootloader_action = QAction("Записать Загрузчик", self)
        burn_bootloader_action.triggered.connect(self._burn_bootloader)
        self.tools_menu.addAction(burn_bootloader_action)

        # Меню "Вид" (для управления видимостью панелей)
        view_menu = menu_bar.addMenu("Вид")
        view_menu.addAction(self.library_dock.toggleViewAction())
        view_menu.addAction(self.code_dock.toggleViewAction())
        view_menu.addAction(self.terminal_dock.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(self.main_toolbar.toggleViewAction())

        # Меню "Помощь"
        help_menu = menu_bar.addMenu("Помощь")
        # Здесь можно добавить действие "О программе"

    def _find_arduino_cli_executable(self):
        """Ищет исполняемый файл arduino-cli в указанной директории Arduino IDE."""
        if self._cli_executable_path: # Используем кэшированный путь, если он есть
            return self._cli_executable_path

        arduino_dir = self.settings_manager.get_setting("arduino_ide_path", "")
        if not arduino_dir or not os.path.exists(arduino_dir):
            return None

        for root, dirs, files in os.walk(arduino_dir):
            if "arduino-cli.exe" in files:
                self._cli_executable_path = os.path.join(root, "arduino-cli.exe")
                return self._cli_executable_path
            elif "arduino-cli" in files: # Для Linux/macOS
                self._cli_executable_path = os.path.join(root, "arduino-cli")
                return self._cli_executable_path
        return None

    def _create_main_layout(self):
        # 1. Центральная область - Холст (основная рабочая зона)
        self.block_canvas = BlockCanvas(self)
        self.setCentralWidget(self.block_canvas)

        # 2. Модульное окно библиотеки (Слева)
        self.library_dock = QDockWidget("Библиотека блоков", self)
        self.library_dock.setObjectName("LibraryDock")
        self.library_panel = LibraryPanel()
        self.library_dock.setWidget(self.library_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library_dock)
        self.library_panel.update_library(self.saved_library)

        # 3. Модульное окно просмотра кода (Справа)
        self.code_dock = QDockWidget("Просмотр кода", self)
        self.code_dock.setObjectName("CodeDock")
        self.code_viewer = CodeViewer()
        self.code_dock.setWidget(self.code_viewer)
        self.addDockWidget(Qt.RightDockWidgetArea, self.code_dock)

        # 4. Модульное окно терминала (Снизу)
        self.terminal_dock = QDockWidget("Терминал", self)
        self.terminal_dock.setObjectName("TerminalDock")
        self.terminal_viewer = TerminalViewer()
        self.terminal_dock.setWidget(self.terminal_viewer)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)

        # Соединяем сигналы
        self.block_canvas.blocks_changed.connect(self._update_code_viewer)
        self.block_canvas.library_save_requested.connect(self._save_to_library_handler)

    def _create_toolbar(self):
        """Создает верхнюю панель инструментов со всеми контроллами."""
        self.main_toolbar = self.addToolBar("Инструменты")
        self.main_toolbar.setObjectName("MainToolBar")
        self.main_toolbar.setMovable(True)
        self.main_toolbar.setIconSize(QSize(20, 20))

        # Выбор платы
        self.main_toolbar.addWidget(QLabel(" Плата: "))
        self.board_selector = QComboBox()
        self.board_selector.setMinimumWidth(180)
        self.board_selector.currentIndexChanged.connect(self._on_board_selected)
        self.main_toolbar.addWidget(self.board_selector)

        # Выбор процессора
        self.main_toolbar.addWidget(QLabel(" Процессор: "))
        self.processor_selector = QComboBox()
        self.processor_selector.currentIndexChanged.connect(self._on_processor_selected)
        self.processor_selector.setMinimumWidth(100)
        self.main_toolbar.addWidget(self.processor_selector)

        # Выбор порта
        self.main_toolbar.addWidget(QLabel(" Порт: "))
        self.port_selector = QComboBox()
        self.port_selector.setMinimumWidth(120)
        self.port_selector.currentIndexChanged.connect(self._on_port_selected)
        self.main_toolbar.addWidget(self.port_selector)

        self.refresh_ports_btn = QPushButton("🔄")
        self.refresh_ports_btn.setFixedSize(28, 28)
        self.refresh_ports_btn.setToolTip("Обновить список портов")
        self.refresh_ports_btn.clicked.connect(self.populate_port_selector)
        self.main_toolbar.addWidget(self.refresh_ports_btn)

        self.main_toolbar.addSeparator()

        # Кнопки действий
        self.compile_btn = QPushButton("🛠 Компилировать")
        self.compile_btn.clicked.connect(self._compile_generated_code)
        self.main_toolbar.addWidget(self.compile_btn)

        self.upload_btn = QPushButton("🚀 Загрузить")
        self.upload_btn.clicked.connect(self._upload_generated_code)
        self.main_toolbar.addWidget(self.upload_btn)

        self.main_toolbar.addSeparator()

        self.save_ino_btn = QPushButton("💾 Сохранить .ino")
        self.save_ino_btn.clicked.connect(self._save_generated_code)
        self.main_toolbar.addWidget(self.save_ino_btn)

    def populate_board_selector(self):
        """Заполняет QComboBox доступными платами Arduino."""
        arduino_dir = self.settings_manager.get_setting("arduino_ide_path", "")
        if not arduino_dir or not os.path.exists(arduino_dir):
            self.board_selector.addItem("Укажите путь к Arduino IDE")
            self.board_selector.setEnabled(False)
            return

        # Ищем arduino-cli
        cli_executable = None
        for root, dirs, files in os.walk(arduino_dir):
            if "arduino-cli.exe" in files:
                cli_executable = os.path.join(root, "arduino-cli.exe")
                break
            elif "arduino-cli" in files: # Для Linux/macOS
                cli_executable = os.path.join(root, "arduino-cli")
                break
        
        if not cli_executable:
            self.board_selector.addItem("arduino-cli не найден")
            self.board_selector.setEnabled(False)
            return

        self.board_selector.setEnabled(True)
        self.board_selector.clear()
        self.processor_selector.clear() # Очищаем процессор при смене платы
        self.board_menu.clear()
        self.processor_menu.clear() # Clear processor menu too
        self.board_options_menu.clear() # Clear other options menu
        self.board_selector.addItem("Загрузка плат...")
        self.board_selector.setEnabled(False) # Временно отключаем на время загрузки

        try:
            # Обновляем индексы плат (может занять время)
            # subprocess.run([cli_executable, "core", "update-index"], capture_output=True, text=True)

            # Получаем список всех доступных плат
            result = subprocess.run([cli_executable, "board", "listall", "--format", "json"], capture_output=True, text=True, check=True, encoding='utf-8')
            data = json.loads(result.stdout)
            boards_list = data.get("boards", [])
            
            self.available_boards = []
            for board in boards_list:
                name = board.get("name")
                fqbn = board.get("fqbn")
                if name and fqbn:
                    self.available_boards.append({"name": name, "fqbn": fqbn})
            
            # Сортируем список по имени для удобства
            self.available_boards.sort(key=lambda x: x["name"])
            
            self.board_selector.clear()
            self.board_menu.clear()
            if not self.available_boards:
                self.board_selector.addItem("Плат не найдено. Установите ядра Arduino.")
                self.board_selector.setEnabled(False)
                self.processor_selector.setEnabled(False)
                self.board_options_menu.clear()
                self.board_options_menu.setEnabled(False)
                self.board_menu.setTitle("Плата: Не найдено")
                return

            for i, board in enumerate(self.available_boards):
                self.board_selector.addItem(board["name"])
                action = self.board_menu.addAction(board["name"])
                action.triggered.connect(lambda checked, idx=i: self.board_selector.setCurrentIndex(idx))
            
            # Get the full saved FQBN to initialize options
            saved_full_fqbn = self.settings_manager.get_setting("selected_board_fqbn")
            initial_base_fqbn = None
            initial_options = {}

            if saved_full_fqbn:
                parts = saved_full_fqbn.split(':')
                initial_base_fqbn = parts[0]
                for part in parts[1:]:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        initial_options[key] = value
            
            self._current_board_config_options = initial_options # Initialize options

            selected_board_index = -1
            for i, board in enumerate(self.available_boards):
                if initial_base_fqbn and board["fqbn"] == initial_base_fqbn:
                    selected_board_index = i
                    break
            
            if selected_board_index != -1:
                self.board_selector.setCurrentIndex(selected_board_index)
                # _on_board_selected will be triggered, which will populate processor and other options
            else:
                # If no saved board or saved board not found, select the first one
                self.board_selector.setCurrentIndex(0)
                # _on_board_selected will be triggered
            self.board_selector.setEnabled(True)

        except subprocess.CalledProcessError as e:
            self.terminal_viewer.append_output(f"Ошибка при получении списка плат: {e.stderr}", color="#FF0000")
            self.board_selector.clear()
            self.board_selector.addItem("Ошибка загрузки плат")
            self.board_selector.setEnabled(False)
        except Exception as e:
            self.board_options_menu.clear()
            self.board_options_menu.setEnabled(False)
            self._current_board_config_options = {}
            self.settings_manager.set_setting("selected_board_fqbn_base", None)
            self.settings_manager.set_setting("selected_board_fqbn", None)
            self.terminal_viewer.append_output(f"Неизвестная ошибка при загрузке плат: {e}", color="#FF0000")
            self.board_selector.clear()
            self.board_selector.addItem("Ошибка загрузки плат")
            self.board_selector.setEnabled(False)


    def populate_port_selector(self):
        """Получает список подключенных портов через arduino-cli."""
        arduino_dir = self.settings_manager.get_setting("arduino_ide_path", "")
        if not arduino_dir:
            self.port_selector.clear()
            self.port_selector.addItem("Укажите путь к IDE")
            return

        cli_executable = None
        for root, dirs, files in os.walk(arduino_dir):
            if "arduino-cli.exe" in files or "arduino-cli" in files:
                cli_executable = os.path.join(root, "arduino-cli.exe" if os.name == 'nt' else "arduino-cli")
                break

        if not cli_executable:
            self.port_selector.clear()
            self.port_selector.addItem("arduino-cli не найден")
            return

        self.port_selector.clear()
        self.port_selector.addItem("Поиск портов...")
        self.port_menu.clear()
        self.port_menu.setTitle("Поиск портов...")
        QApplication.processEvents() # Чтобы текст обновился сразу

        self.port_selector.clear()
        self.port_menu.clear()
        try:
            # Получаем список портов в формате JSON
            result = subprocess.run([cli_executable, "board", "list", "--format", "json"], capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                ports_data = json.loads(result.stdout)
                
                # Улучшенный парсинг разных форматов JSON
                detected_ports = []
                if isinstance(ports_data, list):
                    detected_ports = ports_data
                elif isinstance(ports_data, dict):
                    detected_ports = ports_data.get("detected_ports", ports_data.get("ports", []))
                
                for i, p in enumerate(detected_ports):
                    # Извлекаем адрес порта (обрабатываем вложенный объект "port" или плоскую структуру)
                    port_address = p.get("address")
                    if not port_address and "port" in p:
                        port_val = p["port"]
                        if isinstance(port_val, dict):
                            port_address = port_val.get("address", port_val.get("label", ""))
                        else:
                            port_address = port_val

                    board_name = ""
                    
                    # Пробуем получить название платы
                    matching = p.get("matching_boards", p.get("boards", []))
                    if matching and len(matching) > 0:
                        board_name = f" ({matching[0].get('name', 'Unknown Board')})"
                    
                    if port_address and isinstance(port_address, str):
                        self.port_selector.addItem(f"{port_address}{board_name}", port_address)
                        action = self.port_menu.addAction(f"{port_address}{board_name}")
                        action.triggered.connect(lambda checked, idx=i: self.port_selector.setCurrentIndex(idx))
            else:
                self.terminal_viewer.append_output(f"Ошибка arduino-cli: {result.stderr}", color="#FF0000")
            
            if self.port_selector.count() == 0:
                self.port_selector.addItem("Порты не найдены")
                self.port_menu.setTitle("Порты не найдены")
            else:
                self._on_port_selected(self.port_selector.currentIndex())

        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка при поиске портов: {e}", color="#FF0000")

    def _update_examples_menu(self):
        """Сканирует папки с примерами и заполняет меню."""
        self.examples_menu.clear()
        
        # 1. Встроенные примеры
        arduino_dir = self.settings_manager.get_setting("arduino_ide_path", "")
        if arduino_dir:
            # Проверяем несколько вариантов расположения (для разных версий IDE)
            possible_paths = [
                os.path.join(arduino_dir, "examples"),
                os.path.join(arduino_dir, "resources", "app", "lib", "backend", "resources", "examples") # IDE 2.x
            ]
            for ex_path in possible_paths:
                if os.path.exists(ex_path):
                    self._add_examples_from_dir(ex_path, self.examples_menu.addMenu("Встроенные"))
                    break

        # 2. Примеры библиотек
        sketchbook_path = self.settings_manager.get_setting("sketchbook_path", "")
        if sketchbook_path:
            lib_path = os.path.join(sketchbook_path, "libraries")
            if os.path.exists(lib_path):
                lib_menu = self.examples_menu.addMenu("Примеры библиотек")
                for lib_name in os.listdir(lib_path):
                    lib_ex_dir = os.path.join(lib_path, lib_name, "examples")
                    if os.path.exists(lib_ex_dir):
                        self._add_examples_from_dir(lib_ex_dir, lib_menu.addMenu(lib_name))

    def _add_examples_from_dir(self, directory, menu):
        """Рекурсивно добавляет .ino файлы в указанное меню."""
        try:
            items = os.listdir(directory)
        except (PermissionError, FileNotFoundError):
            return

        for item in sorted(items):
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                # Если внутри есть .ino файл с таким же именем, это папка скетча
                ino_file = os.path.join(path, f"{item}.ino")
                if os.path.exists(ino_file):
                    action = menu.addAction(item)
                    action.triggered.connect(lambda checked, p=ino_file: self._load_example_sketch(p))
                else:
                    # Иначе это просто папка с подкатегориями
                    new_submenu = menu.addMenu(item)
                    self._add_examples_from_dir(path, new_submenu)
                    if not new_submenu.actions():
                        menu.removeAction(new_submenu.menuAction())

    def _load_example_sketch(self, file_path):
        """Загружает код из .ino файла и пытается создать из него структуру блоков."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            reply = QMessageBox.question(self, "Загрузить пример?", 
                                         "Это очистит текущий холст и создаст блоки из примера. Продолжить?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No: return

            self.block_canvas.clear_canvas()
            
            # Улучшенный парсинг: ищем все функции и выделяем глобальную часть
            # Паттерн ищет сигнатуру функции: тип имя(аргументы) {
            func_pattern = re.compile(r"(\w+(?:\s+\w+)?)\s+(\w+)\s*\((.*?)\)\s*\{")
            
            functions = []
            extracted_ranges = []
            
            for match in func_pattern.finditer(content):
                start_index = match.start()
                brace_start = match.end() - 1 # Позиция '{'
                
                # Ищем парную закрывающую скобку '}' с учетом вложенности
                depth = 0
                found_end = -1
                for i in range(brace_start, len(content)):
                    if content[i] == '{':
                        depth += 1
                    elif content[i] == '}':
                        depth -= 1
                        if depth == 0:
                            found_end = i + 1
                            break
                
                if found_end != -1:
                    full_sig = content[start_index:brace_start].strip()
                    body = content[brace_start+1 : found_end-1].strip()
                    func_name = match.group(2)
                    
                    functions.append({
                        'name': func_name,
                        'signature': full_sig,
                        'body': body,
                        'type': 'setup' if func_name == 'setup' else ('loop' if func_name == 'loop' else 'function')
                    })
                    extracted_ranges.append((start_index, found_end))

            # Собираем глобальную часть (все, что вне функций)
            global_parts = []
            current_pos = 0
            for start, end in sorted(extracted_ranges):
                global_parts.append(content[current_pos:start])
                current_pos = end
            global_parts.append(content[current_pos:])
            global_content = "".join(global_parts).strip()

            # Размещаем блоки на холсте с отступом по вертикали
            y_pos = 50
            if global_content:
                self.block_canvas._add_function_block(QPointF(50, y_pos), name="Global", code_content=global_content, block_type="global")
                y_pos += 300

            for func in functions:
                # Для обычных функций имя блока - это полная сигнатура (например, "int readSensor()")
                block_name = func['signature'] if func['type'] == 'function' else func['name']
                self.block_canvas._add_function_block(QPointF(50, y_pos), name=block_name, code_content=func['body'], block_type=func['type'])
                y_pos += 280

            self.terminal_viewer.append_output(f"Пример {os.path.basename(file_path)} импортирован. Найдено функций: {len(functions)}", color="#00FF00")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить пример: {e}")

    def _on_board_selected(self, index):
        """Обработчик выбора платы из QComboBox."""
        if 0 <= index < len(self.available_boards):
            selected_board = self.available_boards[index]
            base_fqbn = selected_board["fqbn"]
            
            # Store the base FQBN
            self.settings_manager.set_setting("selected_board_fqbn_base", base_fqbn)

            # Clear and re-populate processor and other options
            self.processor_selector.clear() # Clear processor selector
            self.processor_menu.clear() # Clear processor menu
            self.processor_menu.setTitle("Процессор: Не выбрана") # Reset title
            self.terminal_viewer.append_output(f"Выбрана плата: {selected_board['name']} ({selected_board['fqbn']})", color="#00FF00")
            self.board_menu.setTitle(f"Плата: \"{selected_board['name']}\"")
            self.populate_processor_selector(selected_board["fqbn"])
            self._populate_other_board_options_menu(selected_board["fqbn"])
        else:
            self.settings_manager.set_setting("selected_board_fqbn", None) # Сбрасываем, если ничего не выбрано
            self.processor_selector.clear()
            self.board_menu.setTitle("Плата: Не выбрана")
            self.processor_selector.setEnabled(False)
            self.board_options_menu.clear()
            self.processor_menu.setTitle("Процессор: Не выбрана")

    def _on_port_selected(self, index):
        """Обработчик выбора порта."""
        if index >= 0 and self.port_selector.itemData(index):
            port_address = self.port_selector.itemData(index)
            self.port_menu.setTitle(f"Порт: \"{port_address}\"")
        else:
            self.port_menu.setTitle("Порт: Не выбран")

    def _on_processor_selected(self, index):
        """Обработчик выбора процессора из QComboBox."""
        if index >= 0 and self.processor_selector.itemData(index):
            processor_name = self.processor_selector.itemText(index)
            processor_value = self.processor_selector.itemData(index)
            self.processor_menu.setTitle(f"Процессор: \"{processor_name}\"")
            self._current_board_config_options["cpu"] = processor_value # Update selected CPU option
            self._update_full_fqbn_from_parts() # Reconstruct full FQBN
        else:
            self.processor_menu.setTitle("Процессор: Не выбран")
            if "cpu" in self._current_board_config_options:
                del self._current_board_config_options["cpu"]
            self._update_full_fqbn_from_parts() # Reconstruct full FQBN


    def populate_processor_selector(self, fqbn):
        """Запрашивает доступные процессоры для выбранной платы."""
        self.processor_selector.clear()
        self.processor_menu.clear()
        self.processor_menu.setTitle("Процессор: Не выбрана")
        self.processor_selector.setEnabled(False) # Disable until options are loaded

        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return
        try:
            # Получаем детали платы в формате JSON
            result = subprocess.run([cli_executable, "board", "details", "-b", fqbn, "--format", "json"], capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                details = json.loads(result.stdout)
                config_options = details.get("config_options", [])
                
                # Ищем опцию 'cpu' (процессор)
                cpu_option = next((opt for opt in config_options if opt.get("option") == "cpu"), None)
                
                if cpu_option:
                    self.processor_selector.setEnabled(True)
                    default_cpu_value = cpu_option.get("default_value")
                    
                    # Get previously selected CPU from full FQBN if available
                    saved_full_fqbn = self.settings_manager.get_setting("selected_board_fqbn")
                    current_cpu_value = None
                    if saved_full_fqbn and ":cpu=" in saved_full_fqbn:
                        match = re.search(r":cpu=([^,:]+)", saved_full_fqbn)
                        if match:
                            current_cpu_value = match.group(1)

                    selected_index = -1
                    for i, val in enumerate(cpu_option.get("values", [])):
                        label = val.get("value_label", val.get("value"))
                        value = val.get("value")
                        self.processor_selector.addItem(label, value)
                        action = self.processor_menu.addAction(label)
                        action.setCheckable(True)
                        action.setData({"option_key": "cpu", "value_key": value})
                        action.triggered.connect(lambda checked, a=action: self._on_board_option_action_triggered(a)) # Use generic handler

                        if value == current_cpu_value:
                            selected_index = i
                            action.setChecked(True)
                            self._current_board_config_options["cpu"] = value
                        elif selected_index == -1 and value == default_cpu_value: # If no saved, use default
                            selected_index = i
                            action.setChecked(True)
                            self._current_board_config_options["cpu"] = value
                    
                    if selected_index != -1:
                        self.processor_selector.setCurrentIndex(selected_index)
                        self.processor_menu.setTitle(f"Процессор: \"{self.processor_selector.currentText()}\"")
                    else: # Fallback if default/saved not found
                        if self.processor_selector.count() > 0:
                            self.processor_selector.setCurrentIndex(0)
                            self.processor_menu.setTitle(f"Процессор: \"{self.processor_selector.currentText()}\"")
                            self._current_board_config_options["cpu"] = self.processor_selector.itemData(0)
                        else:
                            self.processor_menu.setTitle("Процессор: N/A")
                            if "cpu" in self._current_board_config_options:
                                del self._current_board_config_options["cpu"]
                    return
            
            # Если процессоров нет или ошибка
            self.processor_selector.addItem("N/A")
            self.processor_selector.setEnabled(False)
            self.processor_menu.setTitle("Процессор: N/A")
            if "cpu" in self._current_board_config_options:
                del self._current_board_config_options["cpu"]

        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка загрузки процессоров: {e}", color="#FF0000")
            self.processor_selector.setEnabled(False)
            self.processor_menu.setTitle("Процессор: Ошибка")
            if "cpu" in self._current_board_config_options:
                del self._current_board_config_options["cpu"]

    def _populate_other_board_options_menu(self, base_fqbn):
        self.board_options_menu.clear()
        self.board_options_menu.setEnabled(False)

        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return

        try:
            result = subprocess.run([cli_executable, "board", "details", "-b", base_fqbn, "--format", "json"], capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                details = json.loads(result.stdout)
                config_options = details.get("config_options", [])

                # Get previously selected options from full FQBN
                saved_full_fqbn = self.settings_manager.get_setting("selected_board_fqbn")
                
                for config_opt in config_options:
                    option_key = config_opt.get("option")
                    option_label = config_opt.get("option_label", option_key)
                    default_value = config_opt.get("default_value")

                    if not option_key or option_key == "cpu": # Skip 'cpu' as it's handled separately
                        continue

                    submenu = self.board_options_menu.addMenu(option_label)
                    
                    current_option_value = None
                    if saved_full_fqbn and f"{option_key}=" in saved_full_fqbn:
                        match = re.search(rf"[: ,]{option_key}=([^,]+)", saved_full_fqbn)
                        if match:
                            current_option_value = match.group(1)
                    
                    if not current_option_value:
                        current_option_value = default_value

                    for val_data in config_opt.get("values", []):
                        value_key = val_data.get("value")
                        value_label = val_data.get("value_label", value_key)
                        
                        action = submenu.addAction(value_label)
                        action.setCheckable(True)
                        action.setChecked(value_key == current_option_value)
                        action.setData({"option_key": option_key, "value_key": value_key})
                        action.triggered.connect(lambda checked, a=action: self._on_board_option_action_triggered(a))
                        
                        if value_key == current_option_value:
                            self._current_board_config_options[option_key] = value_key
                    
                if self.board_options_menu.actions(): # Only enable if there are actual options
                    self.board_options_menu.setEnabled(True)
                else:
                    self.board_options_menu.setTitle("Параметры платы: Нет")

            else:
                self.terminal_viewer.append_output(f"Ошибка получения деталей платы: {result.stderr}", color="#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка при загрузке параметров платы: {e}", color="#FF0000")
        
        self._update_full_fqbn_from_parts() # Ensure FQBN is updated after populating all options

    def _on_board_option_action_triggered(self, action):
        data = action.data()
        option_key = data["option_key"]
        value_key = data["value_key"]

        # Uncheck other actions in the same submenu
        for sibling_action in action.parent().actions():
            if sibling_action != action:
                sibling_action.setChecked(False)
        action.setChecked(True) # Ensure current action is checked

        self._current_board_config_options[option_key] = value_key
        
        # If the option is 'cpu', also update the QComboBox
        if option_key == "cpu":
            idx = self.processor_selector.findData(value_key)
            if idx != -1:
                self.processor_selector.setCurrentIndex(idx)

        self._update_full_fqbn_from_parts()

    def _update_full_fqbn_from_parts(self):
        base_fqbn = self.settings_manager.get_setting("selected_board_fqbn_base")
        if not base_fqbn:
            self.settings_manager.set_setting("selected_board_fqbn", None)
            return

        options_list = [f"{k}={v}" for k, v in self._current_board_config_options.items()]
        if options_list:
            full_fqbn = f"{base_fqbn}:{','.join(options_list)}"
        else:
            full_fqbn = base_fqbn

        self.settings_manager.set_setting("selected_board_fqbn", full_fqbn)
        self.terminal_viewer.append_output(f"Текущий FQBN для компиляции/загрузки: {full_fqbn}", color="#00FFFF")
        self.statusBar().showMessage(f"Плата: {full_fqbn}")

    def _save_generated_code(self):
        """Сохраняет сгенерированный код в файл .ino"""
        code = self.code_viewer.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "Предупреждение", "Код пуст!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить Arduino код", "", "Arduino Files (*.ino);;All Files (*)")
        if file_path:
            if not file_path.endswith('.ino'):
                file_path += '.ino'
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                QMessageBox.information(self, "Успех", f"Код успешно сохранен:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def _compile_generated_code(self):
        """Компилирует код, используя путь к Arduino IDE из настроек"""
        self.terminal_viewer.clear_output()
        self.terminal_viewer.append_output("Начинаем компиляцию...", color="#FFFF00") # Желтый цвет для начала

        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable:
            QMessageBox.warning(self, "Настройки", "Укажите корректный путь к Arduino IDE в настройках.")
            return

        executable = cli_executable # Для компиляции используем arduino-cli

        if not executable:
            self.terminal_viewer.append_output("Ошибка: Компилятор не найден. Убедитесь, что путь ведет к папке с Arduino IDE.", color="#FF0000")
            return

        generated_files = generate_arduino_code(self.current_project, "sketch")
        temp_dir = tempfile.mkdtemp()
        sketch_name = "sketch"
        sketch_dir = os.path.join(temp_dir, sketch_name)
        os.makedirs(sketch_dir)

        try:
            for fname, content in generated_files.items():
                fpath = os.path.join(sketch_dir, fname)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Подготовка команды (по умолчанию для Arduino Uno)
            selected_fqbn = self.settings_manager.get_setting("selected_board_fqbn")
            if not selected_fqbn:
                self.terminal_viewer.append_output("Ошибка: Плата Arduino не выбрана. Выберите плату в выпадающем списке.", color="#FF0000")
                return

            if "arduino-cli" in executable.lower(): # Всегда используем arduino-cli для компиляции
                cmd = [executable, "compile", "--fqbn", selected_fqbn, sketch_dir]
            else:
                cmd = [executable, "--verify", sketch_path]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                self.terminal_viewer.append_output("\n--- Вывод компилятора (stdout) ---", color="#00FFFF")
                self.terminal_viewer.append_output(result.stdout, color="#00FF00")
                self.terminal_viewer.append_output("\nКомпиляция прошла успешно!", color="#00FF00")
            else:
                self.terminal_viewer.append_output("\n--- Вывод компилятора (stderr) ---", color="#FF00FF")
                self.terminal_viewer.append_output(result.stderr if result.stderr else result.stdout, color="#FF0000")
                self.terminal_viewer.append_output("\nКомпиляция завершилась с ошибками!", color="#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"\nКритическая ошибка при запуске компиляции: {e}", color="#FF0000")
        finally:
            shutil.rmtree(temp_dir)

    def _upload_generated_code(self):
        """Компилирует и загружает код на плату."""
        self.terminal_viewer.clear_output()
        
        arduino_dir = self.settings_manager.get_setting("arduino_ide_path", "")
        selected_fqbn = self.settings_manager.get_setting("selected_board_fqbn") # Получаем FQBN платы
        port = self.port_selector.currentData() # Получаем адрес порта из userData

        if port:
             self.statusBar().showMessage(f"Загрузка на {selected_fqbn} через {port}...")

        if not arduino_dir or not selected_fqbn or not port:
            QMessageBox.warning(self, "Загрузка", "Проверьте путь к IDE, выберите плату и порт!")
            return

        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return
        
        generated_files = generate_arduino_code(self.current_project)
        temp_dir = tempfile.mkdtemp()
        sketch_name = "sketch"
        sketch_dir = os.path.join(temp_dir, sketch_name)
        os.makedirs(sketch_dir)

        try:
            for fname, content in generated_files.items():
                fpath = os.path.join(sketch_dir, fname)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)

            self.terminal_viewer.append_output("Шаг 1: Компиляция перед загрузкой...", color="#FFFF00")
            
            # Сначала компилируем
            compile_cmd = [cli_executable, "compile", "--fqbn", selected_fqbn, sketch_dir]
            res_comp = subprocess.run(compile_cmd, capture_output=True, text=True, encoding='utf-8')
            
            if res_comp.returncode != 0:
                self.terminal_viewer.append_output("Ошибка компиляции:\n" + res_comp.stderr, color="#FF0000")
                return

            self.terminal_viewer.append_output("Шаг 2: Загрузка в плату...", color="#FFFF00")
            
            # Затем загружаем
            upload_cmd = [cli_executable, "upload", "-p", port, "--fqbn", selected_fqbn, sketch_dir]
            res_up = subprocess.run(upload_cmd, capture_output=True, text=True, encoding='utf-8')

            if res_up.returncode == 0:
                self.terminal_viewer.append_output(res_up.stdout, color="#00FF00")
                self.terminal_viewer.append_output("\nЗагрузка завершена успешно! 🚀", color="#00FF00")
            else:
                self.terminal_viewer.append_output("Ошибка загрузки:\n" + res_up.stderr, color="#FF0000")

        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка: {e}", color="#FF0000")
        finally:
            shutil.rmtree(temp_dir)

    def _open_settings(self):
        # Получаем текущий путь из настроек
        current_path = self.settings_manager.get_setting("arduino_ide_path", "")
        current_sketchbook = self.settings_manager.get_setting("sketchbook_path", "")
        current_library = self.settings_manager.get_setting("library_path", self.library_dir)
        current_pdf_path = self.settings_manager.get_setting("pdf_docs_path", os.path.join(current_dir, "docs"))

        dialog = SettingsDialog(current_path, current_sketchbook, current_library, current_pdf_path, self)
        dialog.install_library_requested.connect(self._handle_install_library_request)
        dialog.install_library_from_zip_requested.connect(self._handle_install_library_from_zip_request)
        dialog.search_library_requested.connect(lambda q: self._handle_search_library_request(q, dialog))
        dialog.update_index_requested.connect(self._handle_update_index_request)
        dialog.list_installed_requested.connect(lambda: self._handle_list_libraries_request(dialog))
        dialog.uninstall_library_requested.connect(self._handle_uninstall_library_request)

        if dialog.exec_() == QDialog.Accepted: # Если пользователь нажал "Сохранить"
            new_path = dialog.get_arduino_path()
            new_sketchbook = dialog.get_sketchbook_path()
            new_pdf_path = dialog.get_pdf_path()
            new_library = dialog.get_library_path()

            # Обработка изменения пути к Arduino IDE
            if new_path != current_path:
                self.settings_manager.set_setting("arduino_ide_path", new_path)
                self.populate_board_selector() # Обновляем список плат при изменении пути к IDE

            if new_sketchbook != current_sketchbook:
                self.settings_manager.set_setting("sketchbook_path", new_sketchbook)
                self._sync_arduino_cli_config(new_sketchbook)

            if new_pdf_path != current_pdf_path:
                self.settings_manager.set_setting("pdf_docs_path", new_pdf_path)

            # После сохранения настроек обязательно обновляем меню примеров
            self._update_examples_menu()

            if new_library != current_library:
                self.settings_manager.set_setting("library_path", new_library)
                self.library_dir = new_library
                self.library_panel.update_library(self._load_library())

            QMessageBox.information(self, "Настройки сохранены", "Настройки успешно обновлены.")

    def _sync_arduino_cli_config(self, sketchbook_path):
        """Синхронизирует настройки arduino-cli с выбранной папкой скетчей."""
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable or not sketchbook_path:
            return

        try:
            # Устанавливаем directories.user через arduino-cli config set
            subprocess.run([cli_executable, "config", "set", "directories.user", sketchbook_path], 
                           capture_output=True, text=True, encoding='utf-8', check=True)
            self.terminal_viewer.append_output(f"Конфигурация arduino-cli обновлена. Sketchbook: {sketchbook_path}", color="#00FF00")
        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка при обновлении конфига arduino-cli: {e}", color="#FF0000")

    def _load_library(self):
        """Загружает библиотеку блоков из указанной папки."""
        if not os.path.exists(self.library_dir):
            os.makedirs(self.library_dir, exist_ok=True)
            return []
            
        library_data = []
        for file_name in os.listdir(self.library_dir):
            if file_name.endswith(".json"):
                try:
                    path = os.path.join(self.library_dir, file_name)
                    with open(path, 'r', encoding='utf-8') as f:
                        block_data = json.load(f)
                        # Ищем превью
                        preview_path = path.replace(".json", ".png")
                        if os.path.exists(preview_path):
                            block_data["_preview_path"] = preview_path
                        library_data.append(block_data)
                except:
                    continue
        return library_data

    def _handle_install_library_request(self, library_name: str):
        """Обрабатывает запрос на установку библиотеки Arduino."""
        self.terminal_viewer.append_output(f"Запрос на установку библиотеки: {library_name}...", color="#FFFF00")
        
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable:
            self.terminal_viewer.append_output("Ошибка: Укажите корректный путь к Arduino IDE в настройках.", color="#FF0000")
            return

        try:
            cmd = [cli_executable, "lib", "install", library_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            self.terminal_viewer.append_output(f"Библиотека '{library_name}' успешно установлена:\n{result.stdout}", color="#00FF00")
        except subprocess.CalledProcessError as e:
            self.terminal_viewer.append_output(f"Ошибка при установке библиотеки '{library_name}':\n{e.stderr}", color="#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"Неизвестная ошибка при установке библиотеки '{library_name}': {e}", color="#FF0000")

    def _handle_install_library_from_zip_request(self, zip_file_path: str):
        """Обрабатывает запрос на установку библиотеки Arduino из ZIP-файла."""
        self.terminal_viewer.append_output(f"Запрос на установку библиотеки из ZIP: {os.path.basename(zip_file_path)}...", color="#FFFF00")
        
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable:
            self.terminal_viewer.append_output("Ошибка: Укажите корректный путь к Arduino IDE в настройках.", color="#FF0000")
            return

        if not os.path.exists(zip_file_path):
            self.terminal_viewer.append_output(f"Ошибка: ZIP-файл не найден по пути: {zip_file_path}", color="#FF0000")
            return

        try:
            # arduino-cli lib install --zip-path <path/to/library.zip>
            cmd = [cli_executable, "lib", "install", "--zip-path", zip_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            self.terminal_viewer.append_output(f"Библиотека из ZIP '{os.path.basename(zip_file_path)}' успешно установлена:\n{result.stdout}", color="#00FF00")
        except subprocess.CalledProcessError as e:
            self.terminal_viewer.append_output(f"Ошибка при установке библиотеки из ZIP '{os.path.basename(zip_file_path)}':\n{e.stderr}", color="#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"Неизвестная ошибка при установке библиотеки из ZIP '{os.path.basename(zip_file_path)}': {e}", color="#FF0000")

    def _handle_update_index_request(self):
        """Обновляет индекс библиотек через arduino-cli."""
        self.terminal_viewer.append_output("Обновление индекса библиотек из интернета...", color="#FFFF00")
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return

        try:
            result = subprocess.run([cli_executable, "lib", "update-index"], 
                                    capture_output=True, text=True, encoding='utf-8', check=True)
            self.terminal_viewer.append_output("Индекс библиотек успешно обновлен!", color="#00FF00")
            if result.stdout: self.terminal_viewer.append_output(result.stdout, color="#888888")
        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка обновления индекса: {e}", color="#FF0000")

    def _handle_search_library_request(self, query: str, dialog: SettingsDialog):
        """Ищет библиотеки и передает результаты обратно в диалог."""
        self.terminal_viewer.append_output(f"Поиск библиотеки: {query}...", color="#FFFF00")
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return

        try:
            # Выполняем поиск с выводом в формате JSON
            result = subprocess.run([cli_executable, "lib", "search", query, "--format", "json"], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                self.terminal_viewer.append_output(f"Ошибка поиска: {result.stderr}", color="#FF0000")
                return

            stdout_text = result.stdout if result.stdout else "{}"
            data = json.loads(stdout_text)
            libraries = data.get("libraries", []) if isinstance(data, dict) else []
            
            if libraries:
                dialog.display_search_results(libraries)
                self.terminal_viewer.append_output(f"Найдено библиотек: {len(libraries)}", color="#00FF00")
            else:
                dialog.display_search_results([])
                self.terminal_viewer.append_output("Библиотеки не найдены.", color="#FF0000")
                
        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка поиска: {e}", color="#FF0000")

    def _handle_list_libraries_request(self, dialog: SettingsDialog):
        """Получает список установленных библиотек."""
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return

        try:
            # Проверяем текущую конфигурацию путей
            config_res = subprocess.run([cli_executable, "config", "dump", "--format", "json"], 
                                         capture_output=True, text=True, encoding='utf-8')
            user_dir = "Не определен"
            if config_res.returncode == 0:
                config_data = json.loads(config_res.stdout)
                user_dir = config_data.get("directories", {}).get("user", "Не определен")
            
            self.terminal_viewer.append_output(f"Поиск библиотек в: {user_dir}", color="#ADD8E6")

            result = subprocess.run([cli_executable, "lib", "list", "--format", "json"], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                return

            stdout_text = result.stdout if result.stdout else "[]"
            
            try:
                data = json.loads(stdout_text)
                # Обработка разных ключей: 'installed_libraries' (новые версии) или 'libraries'
                if isinstance(data, list):
                    libraries = data
                elif isinstance(data, dict):
                    # Проверяем оба варианта ключей
                    libraries = data.get("installed_libraries", data.get("libraries", []))
                else:
                    libraries = []

                self.terminal_viewer.append_output(f"Установлено библиотек: {len(libraries)}", color="#ADD8E6")
                dialog.display_installed_libraries(libraries)
                
            except json.JSONDecodeError as e:
                self.terminal_viewer.append_output(f"Ошибка парсинга JSON: {e}", color="#FF0000")

        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка получения списка библиотек: {e}", color="#FF0000")

    def _handle_uninstall_library_request(self, library_name: str):
        """Удаляет указанную библиотеку."""
        self.terminal_viewer.append_output(f"Удаление библиотеки: {library_name}...", color="#FFFF00")
        cli_executable = self._find_arduino_cli_executable()
        if not cli_executable: return

        try:
            # Пытаемся удалить. В arduino-cli команда: lib uninstall
            cmd = [cli_executable, "lib", "uninstall", library_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            self.terminal_viewer.append_output(f"Библиотека '{library_name}' успешно удалена.", color="#00FF00")
            
            # После удаления можно было бы обновить список, но так как это в диалоге,
            # пользователю проще нажать "Обновить" или зайти снова.
        except subprocess.CalledProcessError as e:
            # Некоторые библиотеки (встроенные) могут не удаляться
            self.terminal_viewer.append_output(f"Ошибка удаления: {e.stderr}", color="#FF0000")
            QMessageBox.warning(None, "Удаление", f"Не удалось удалить библиотеку. Возможно, она является встроенной.\n{e.stderr}")
        except Exception as e:
            self.terminal_viewer.append_output(f"Критическая ошибка при удалении: {e}", color="#FF0000")

    def _save_to_library_handler(self, block_widget):
        """Сохраняет блок и его превью в папку библиотеки."""
        data_dict = block_widget.block_data.to_dict()
        
        # Удаляем специфичные данные проекта перед сохранением в общую библиотеку
        if "id" in data_dict: del data_dict["id"]
        
        if not os.path.exists(self.library_dir):
            os.makedirs(self.library_dir, exist_ok=True)

        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', data_dict['name'])
        base_path = os.path.join(self.library_dir, safe_name)
        
        # Сохраняем JSON
        with open(base_path + ".json", 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=4, ensure_ascii=False)
            
        # Захватываем превью виджета
        pixmap = block_widget.proxy_widget.widget().grab()
        pixmap.save(base_path + ".png")
            
        self.library_panel.update_library(self._load_library())
        QMessageBox.information(self, "Библиотека", f"Блок '{data_dict['name']}' сохранен в библиотеку блоков.")

    def _new_project(self):
        reply = QMessageBox.question(self, "Новый проект",
                                     "Вы уверены, что хотите создать новый проект? Несохраненные изменения будут потеряны.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.current_project = BlockProject()
            self.block_canvas.clear_canvas()
            self.block_canvas.add_default_blocks() # Добавляем стандартные блоки при новом проекте
            self._update_code_viewer()
            QMessageBox.information(self, "Новый проект", "Новый проект создан.")

    def _open_project(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть проект", "", "Block Editor Projects (*.json);;All Files (*)")
        if file_name:
            try:
                self.current_project = BlockProject.load_from_file(file_name)
                self.block_canvas.load_project(self.current_project)
                self._update_code_viewer()
                QMessageBox.information(self, "Открыть проект", f"Проект '{file_name}' успешно открыт.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка открытия", f"Не удалось открыть проект: {e}")

    def _save_project(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "", "Block Editor Projects (*.json);;All Files (*)")
        if file_name:
            try:
                # 1. Получаем базовое имя проекта (без расширения) и директорию
                project_dir = os.path.dirname(file_name)
                project_base_name = os.path.splitext(os.path.basename(file_name))[0]
                
                # 2. Создаем папку для Arduino IDE (с тем же именем, что и JSON)
                sketch_folder = os.path.join(project_dir, project_base_name)
                os.makedirs(sketch_folder, exist_ok=True)
                
                # 3. Получаем данные и генерируем код для всех файлов
                self.current_project = self.block_canvas.get_current_project_data()
                generated_files = generate_arduino_code(self.current_project, project_base_name)
                
                # 4. Сохраняем все сгенерированные файлы (.ino, .h, .cpp) в созданную папку
                for fname, content in generated_files.items():
                    with open(os.path.join(sketch_folder, fname), 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # 5. Сохраняем JSON файл метаданных нашего редактора рядом с папкой
                self.current_project.save_to_file(file_name)
                QMessageBox.information(self, "Сохранить проект", f"Проект успешно сохранен!\n\nJSON: {file_name}\nПапка IDE: {sketch_folder}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить проект: {e}")

    def _export_project_bundle(self):
        """Экспортирует проект и все зависимые библиотеки в одну папку."""
        # 1. Выбор папки для экспорта
        base_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для экспорта проекта")
        if not base_dir:
            return

        # Запрашиваем имя проекта (папки)
        project_name, ok = QInputDialog.getText(self, "Имя проекта", "Введите название папки проекта:", QLineEdit.Normal, "ArduinoProjectBundle")
        if not ok or not project_name:
            return

        target_dir = os.path.join(base_dir, project_name)
        if os.path.exists(target_dir):
            reply = QMessageBox.question(self, "Папка существует", "Папка уже существует. Перезаписать?", 
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No: return
            shutil.rmtree(target_dir)
        
        os.makedirs(target_dir)
        lib_target_dir = os.path.join(target_dir, "libraries")

        try:
            # 2. Сохраняем .ino и .json
            code = self.code_viewer.toPlainText()
            with open(os.path.join(target_dir, f"{project_name}.ino"), 'w', encoding='utf-8') as f:
                f.write(code)
            
            project_data = self.block_canvas.get_current_project_data()
            project_data.save_to_file(os.path.join(target_dir, "project_blocks.json"))

            # 3. Поиск библиотек
            self.terminal_viewer.append_output("Начинаем поиск и экспорт библиотек...", color="#FFFF00")
            
            # Находим все #include <Header.h> или #include "Header.h"
            includes = re.findall(r'#include\s*[<"]\s*([^>"\s]+)\.h\s*[>"]', code)
            unique_headers = set(includes)
            
            # Список стандартных библиотек ядра, которые не нужно экспортировать
            CORE_LIBRARIES = {"arduino", "eeprom", "spi", "wire", "softwareserial", "hid", "servo", "avr", "util", "usb"}

            if unique_headers:
                cli_executable = self._find_arduino_cli_executable()
                if cli_executable:
                    # Получаем список установленных библиотек
                    result = subprocess.run([cli_executable, "lib", "list", "--format", "json"], 
                                            capture_output=True, text=True, encoding='utf-8')
                    if result.returncode == 0:
                        stdout_text = result.stdout if result.stdout else "[]"
                        try:
                            data = json.loads(stdout_text)
                            if isinstance(data, list):
                                installed_libs = data
                            elif isinstance(data, dict):
                                installed_libs = data.get("installed_libraries", data.get("libraries", []))
                            else:
                                installed_libs = []
                        except:
                            installed_libs = []
                        
                        exported_count = 0
                        os.makedirs(lib_target_dir, exist_ok=True)

                        for header in unique_headers:
                            # Очистка и проверка на системные библиотеки
                            clean_header = header.replace('\\', '/').strip('/')
                            header_root = clean_header.split('/')[0].lower()
                            if header_root in CORE_LIBRARIES:
                                continue
                            
                            found_path = None
                            lib_full_name = ""
                            
                            # Ищем библиотеку, которая содержит этот заголовок
                            for entry in installed_libs:
                                # Обрабатываем возможную вложенность "library"
                                lib_info = entry.get("library") if isinstance(entry.get("library"), dict) else entry
                                if not isinstance(lib_info, dict): continue
                                
                                name = lib_info.get("name", "")
                                
                                # Поиск пути (разные ключи в разных версиях CLI)
                                path = ""
                                for p_key in ["install_dir", "location", "path"]:
                                    p_val = lib_info.get(p_key)
                                    if p_val:
                                        if isinstance(p_val, dict):
                                            path = p_val.get("path", "")
                                        else:
                                            path = str(p_val)
                                        if path and os.path.exists(path):
                                            break
                                
                                if not path: continue

                                # Сравнение имен (удаляем все не-буквенно-цифровые символы)
                                norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                                norm_header = re.sub(r'[^a-zA-Z0-9]', '', clean_header.lower())
                                header_filename = os.path.basename(clean_header)

                                if norm_name == norm_header or \
                                   os.path.exists(os.path.join(path, f"{header_filename}.h")) or \
                                   os.path.exists(os.path.join(path, "src", f"{header_filename}.h")):
                                    found_path = path
                                    lib_full_name = name
                                    break
                            
                            if found_path:
                                lib_folder_name = os.path.basename(os.path.normpath(found_path))
                                dest_path = os.path.join(lib_target_dir, lib_folder_name)
                                if not os.path.exists(dest_path):
                                    try:
                                        shutil.copytree(found_path, dest_path)
                                        self.terminal_viewer.append_output(f"Библиотека скопирована: {lib_full_name}", color="#00FF00")
                                        exported_count += 1
                                    except Exception as e:
                                        self.terminal_viewer.append_output(f"Ошибка копирования {lib_full_name}: {e}", color="#FF0000")
                            else:
                                self.terminal_viewer.append_output(f"Предупреждение: Не удалось найти исходники для <{header}.h>", color="#FF0000")

                        self.terminal_viewer.append_output(f"Экспорт завершен. Успешно скопировано библиотек: {exported_count}", color="#00FF00")
            
            # 4. Финальное сообщение
            QMessageBox.information(self, "Экспорт завершен", 
                                    f"Проект успешно экспортирован в:\n{target_dir}\n\n"
                                    "Вы можете передать эту папку другому пользователю.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Произошла ошибка при экспорте: {e}")

    def _update_code_viewer(self):
        self.current_project = self.block_canvas.get_current_project_data()
        # Используем "sketch" как имя по умолчанию для совместимости
        generated_files = generate_arduino_code(self.current_project, "sketch")
        self.code_viewer.set_code_files(generated_files)

    def _auto_format_code(self):
        """Примитивное автоформатирование кода внутри блоков (выравнивание отступов)."""
        self.terminal_viewer.append_output("Выполняется форматирование кода в блоках...", color="#FFFF00")
        for block in self.block_canvas.blocks:
            lines = block.block_data.code_content.split('\n')
            formatted_lines = []
            indent_level = 0
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    formatted_lines.append("")
                    continue
                if stripped.startswith('}'):
                    indent_level = max(0, indent_level - 1)
                
                formatted_lines.append("    " * indent_level + stripped)
                
                if stripped.endswith('{'):
                    indent_level += 1
            
            block.code_editor.setPlainText('\n'.join(formatted_lines))
        self._update_code_viewer()
        self.terminal_viewer.append_output("Форматирование завершено.", color="#00FF00")

    def _archive_project(self):
        """Создает ZIP-архив с текущим проектом (.json и .ino)."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Архивировать проект", "", "ZIP Files (*.zip)")
        if not file_path:
            return

        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем данные блоков
                project_data = self.block_canvas.get_current_project_data()
                json_str = json.dumps(project_data.to_dict(), indent=4, ensure_ascii=False)
                zipf.writestr("project.json", json_str)
                
                # Добавляем сгенерированный код
                zipf.writestr("sketch.ino", self.code_viewer.toPlainText())
                
            QMessageBox.information(self, "Архивация", f"Проект успешно сохранен в архив:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка архивации", f"Не удалось создать архив: {e}")

    def _open_serial_monitor(self):
        """Открывает полноценное окно монитора порта. 
        Импорт выполняется внутри метода для предотвращения падения программы при отсутствии pyserial.
        """
        try:
            from ui.serial_monitor import SerialMonitorWindow
        except ImportError:
            self.terminal_viewer.append_output("Ошибка: Модуль 'pyserial' не найден.", color="#FF0000")
            QMessageBox.critical(self, "Ошибка библиотеки", 
                                 "Библиотека 'pyserial' не установлена в папке libs.\n\n"
                                 "Пожалуйста, проверьте установку в терминале.")
            return

        port = self.port_selector.currentData()
        if not port:
            QMessageBox.warning(self, "Монитор порта", "Пожалуйста, сначала выберите порт.")
            return

        if self.serial_monitor and self.serial_monitor.isVisible():
            self.serial_monitor.close()

        try:
            self.serial_monitor = SerialMonitorWindow(port)
            self.serial_monitor.show()
            self.terminal_viewer.append_output(f"Запущен монитор порта на {port}", color="#00FFFF")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка монитора порта", f"Не удалось запустить монитор: {e}")

    def _get_board_info(self):
        """Запрашивает информацию о плате через arduino-cli."""
        port = self.port_selector.currentData()
        fqbn = self.settings_manager.get_setting("selected_board_fqbn")
        cli = self._find_arduino_cli_executable()
        
        if not cli or not port or not fqbn:
            QMessageBox.warning(self, "Информация о плате", "Выберите плату и порт для получения информации.")
            return
            
        self.terminal_viewer.append_output(f"Запрос подробной информации для {fqbn} на {port}...", color="#FFFF00")
        try:
            res = subprocess.run([cli, "board", "details", "-b", fqbn], capture_output=True, text=True, encoding='utf-8')
            self.terminal_viewer.append_output(res.stdout if res.returncode == 0 else res.stderr, 
                                               color="#00FF00" if res.returncode == 0 else "#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"Ошибка: {e}", color="#FF0000")

    def _burn_bootloader(self):
        """Записывает загрузчик в плату."""
        port = self.port_selector.currentData()
        fqbn = self.settings_manager.get_setting("selected_board_fqbn")
        cli = self._find_arduino_cli_executable()
        
        if not cli or not port or not fqbn:
            QMessageBox.warning(self, "Загрузчик", "Выберите плату и порт.")
            return
            
        reply = QMessageBox.question(self, "Записать загрузчик?", 
                                     "Вы уверены? Это действие перезапишет загрузчик на подключенном устройстве.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            return
            
        self.terminal_viewer.append_output("Запуск процесса записи загрузчика...", color="#FFFF00")
        try:
            # Команда: arduino-cli burn-bootloader -b <fqbn> -p <port>
            res = subprocess.run([cli, "burn-bootloader", "-b", fqbn, "-p", port], capture_output=True, text=True, encoding='utf-8')
            self.terminal_viewer.append_output(res.stdout if res.returncode == 0 else res.stderr, 
                                               color="#00FF00" if res.returncode == 0 else "#FF0000")
        except Exception as e:
            self.terminal_viewer.append_output(f"Критическая ошибка: {e}", color="#FF0000")

    def _open_calculator(self):
        """Открывает окно продвинутого калькулятора."""
        if self.calculator_window is None:
            self.calculator_window = CalculatorWindow(self)
        
        if not self.calculator_window.isVisible():
            self.calculator_window.show()
        self.calculator_window.raise_() # Поднимаем окно на передний план

    def _open_pdf_viewer(self):
        """Открывает окно просмотра PDF документации."""
        if self.pdf_viewer_window is None:
            self.pdf_viewer_window = PDFViewerWindow(self)
        
        if not self.pdf_viewer_window.isVisible():
            self.pdf_viewer_window.show()
        self.pdf_viewer_window.raise_()
