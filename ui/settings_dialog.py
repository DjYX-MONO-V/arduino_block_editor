# ui/settings_dialog.py
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QGroupBox, QListWidget, QListWidgetItem, QTabWidget, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

class SettingsDialog(QDialog):
    def __init__(self, current_arduino_path: str = "", current_sketchbook_path: str = "", current_library_path: str = "", current_pdf_path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 600, 500)
        self.setModal(True) # Делаем диалог модальным (блокирует родительское окно)

        self.arduino_path = current_arduino_path
        self.sketchbook_path = current_sketchbook_path
        self.library_path = current_library_path
        self.pdf_path = current_pdf_path
        self._init_ui()
    
    install_library_requested = pyqtSignal(str) # Сигнал для запроса установки библиотеки
    install_library_from_zip_requested = pyqtSignal(str) # Сигнал для запроса установки библиотеки из ZIP
    search_library_requested = pyqtSignal(str) # Сигнал для поиска библиотек
    update_index_requested = pyqtSignal() # Сигнал для обновления индекса библиотек
    list_installed_requested = pyqtSignal() # Запрос списка установленных
    uninstall_library_requested = pyqtSignal(str) # Запрос удаления

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Секция для пути к Arduino IDE
        path_layout = QHBoxLayout()
        path_label = QLabel("Путь к Arduino IDE:")
        self.path_line_edit = QLineEdit(self.arduino_path)
        self.path_line_edit.setPlaceholderText("Например: C:/Program Files (x86)/Arduino")
        self.path_line_edit.textChanged.connect(self._on_path_changed)
        
        browse_button = QPushButton("Обзор...")
        browse_button.clicked.connect(self._browse_arduino_path)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_line_edit)
        path_layout.addWidget(browse_button)
        main_layout.addLayout(path_layout)

        # Секция для пути к папке скетчей (Sketchbook)
        sketchbook_layout = QHBoxLayout()
        sketchbook_label = QLabel("Папка скетчей (Sketchbook):")
        self.sketchbook_line_edit = QLineEdit(self.sketchbook_path)
        self.sketchbook_line_edit.setPlaceholderText("Обычно: Documents/Arduino")
        self.sketchbook_line_edit.textChanged.connect(self._on_sketchbook_changed)

        browse_sketchbook_btn = QPushButton("Обзор...")
        browse_sketchbook_btn.clicked.connect(self._browse_sketchbook_path)

        sketchbook_layout.addWidget(sketchbook_label)
        sketchbook_layout.addWidget(self.sketchbook_line_edit)
        sketchbook_layout.addWidget(browse_sketchbook_btn)
        main_layout.addLayout(sketchbook_layout)

        # Секция для пути к библиотеке блоков
        library_path_layout = QHBoxLayout()
        library_path_label = QLabel("Папка библиотеки блоков:")
        self.library_path_line_edit = QLineEdit(self.library_path)
        self.library_path_line_edit.setPlaceholderText("Папка для сохранения шаблонов блоков")
        
        browse_library_btn = QPushButton("Обзор...")
        browse_library_btn.clicked.connect(self._browse_library_path)

        library_path_layout.addWidget(library_path_label)
        library_path_layout.addWidget(self.library_path_line_edit)
        library_path_layout.addWidget(browse_library_btn)
        main_layout.addLayout(library_path_layout)

        # Секция для пути к папке с PDF (Документация)
        pdf_path_layout = QHBoxLayout()
        pdf_label = QLabel("Папка с документацией (PDF):")
        self.pdf_path_line_edit = QLineEdit(self.pdf_path)
        self.pdf_path_line_edit.setPlaceholderText("Папка с учебными материалами")
        
        browse_pdf_btn = QPushButton("Обзор...")
        browse_pdf_btn.clicked.connect(self._browse_pdf_path)

        pdf_path_layout.addWidget(pdf_label)
        pdf_path_layout.addWidget(self.pdf_path_line_edit)
        pdf_path_layout.addWidget(browse_pdf_btn)
        main_layout.addLayout(pdf_path_layout)


        # Секция для управления библиотеками
        self.tabs = QTabWidget()
        
        # --- Вкладка 1: Поиск и установка ---
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)

        update_btn = QPushButton("Обновить индекс библиотек (из интернета)")
        update_btn.clicked.connect(self.update_index_requested.emit)
        search_layout.addWidget(update_btn)

        install_library_layout = QHBoxLayout()
        self.library_name_input = QLineEdit()
        self.library_name_input.setPlaceholderText("Поиск или название библиотеки...")
        self.library_name_input.returnPressed.connect(self._on_search_clicked)
        
        search_button = QPushButton("🔍 Поиск")
        search_button.clicked.connect(self._on_search_clicked)

        install_button = QPushButton("Установить библиотеку")
        install_button.clicked.connect(self._on_install_library_clicked)

        install_library_layout.addWidget(self.library_name_input)
        install_library_layout.addWidget(search_button)
        install_library_layout.addWidget(install_button)
        search_layout.addLayout(install_library_layout)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        search_layout.addWidget(self.results_list)
        
        install_zip_button = QPushButton("Добавить .ZIP библиотеку...")
        install_zip_button.clicked.connect(self._on_install_zip_library_clicked)
        search_layout.addWidget(install_zip_button)

        self.tabs.addTab(search_tab, "Поиск и установка")

        # --- Вкладка 2: Установленные библиотеки ---
        installed_tab = QWidget()
        installed_layout = QVBoxLayout(installed_tab)

        refresh_installed_btn = QPushButton("🔄 Обновить список установленных")
        refresh_installed_btn.clicked.connect(self.list_installed_requested.emit)
        installed_layout.addWidget(refresh_installed_btn)

        self.installed_list = QListWidget()
        installed_layout.addWidget(self.installed_list)

        uninstall_btn = QPushButton("Удалить выбранную библиотеку")
        uninstall_btn.clicked.connect(self._on_uninstall_clicked)
        uninstall_btn.setStyleSheet("background-color: #A33; color: white;")
        installed_layout.addWidget(uninstall_btn)

        self.tabs.addTab(installed_tab, "Установленные")
        main_layout.addWidget(self.tabs)

        # Подгружаем список при открытии вкладки "Установленные"
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Кнопки (Сохранить/Отмена)
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept) # QDialog.accept() закрывает диалог с результатом Accepted
        self.save_button.setEnabled(bool(self.arduino_path)) # Изначально кнопка активна, если путь уже есть
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject) # QDialog.reject() закрывает диалог с результатом Rejected

        button_layout.addStretch() # Выравнивает кнопки вправо
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def _browse_arduino_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку установки Arduino IDE", self.arduino_path)
        if directory:
            self.path_line_edit.setText(directory)

    def _browse_sketchbook_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку со скетчами (Sketchbook)", self.sketchbook_path)
        if directory:
            self.sketchbook_line_edit.setText(directory)

    def _browse_library_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку библиотеки блоков", self.library_path)
        if directory:
            self.library_path_line_edit.setText(directory)

    def _browse_pdf_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку с PDF файлами", self.pdf_path)
        if directory:
            self.pdf_path_line_edit.setText(directory)

    def _on_path_changed(self, text):
        self.arduino_path = text
        self.save_button.setEnabled(bool(text)) # Активируем кнопку "Сохранить", если путь не пуст

    def _on_sketchbook_changed(self, text):
        self.sketchbook_path = text

    def get_sketchbook_path(self):
        return self.sketchbook_path

    def get_library_path(self):
        return self.library_path_line_edit.text()

    def get_pdf_path(self):
        return self.pdf_path_line_edit.text()

    def get_arduino_path(self):
        return self.arduino_path

    def display_search_results(self, libraries):
        """Отображает результаты поиска в списке."""
        self.results_list.clear()
        for lib in libraries:
            name = lib.get("name", "Unknown")
            version = lib.get("latest", {}).get("version", "")
            sentence = lib.get("sentence", "")
            
            item_text = f"{name} ({version})\n{sentence}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name) # Сохраняем чистое имя для установки
            self.results_list.addItem(item)

    def display_installed_libraries(self, libraries):
        """Отображает установленные библиотеки."""
        self.installed_list.clear()
        for lib_data in libraries: # lib_data is a dictionary for each library
            name = lib_data.get("name")
            version = lib_data.get("version")
            location_info = lib_data.get("location") # This can be a dict or None

            # Если не найдено напрямую, пробуем вложенный ключ 'library'
            # This part might be for older arduino-cli versions or different commands
            # For 'lib list', name and version are usually top-level.
            if not name and isinstance(lib_data.get("library"), dict):
                nested_lib = lib_data["library"]
                name = nested_lib.get("name")
                version = nested_lib.get("version")
                if not location_info: # Only update if not already found at top level
                    location_info = nested_lib.get("location")
            
            if not name: # Если имя все еще не найдено, используем заглушку
                name = "Unknown Library"
            if not version:
                version = "N/A"
            
            loc_str = ""
            if isinstance(location_info, dict):
                if location_info.get("type") == "builtin":
                    loc_str = " (Встроенная)"
            elif isinstance(location_info, str) and "builtin" in location_info.lower():
                loc_str = " (Встроенная)"

            item_text = f"{name} - Версия: {version}{loc_str}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.installed_list.addItem(item)

    def _on_search_clicked(self):
        query = self.library_name_input.text().strip()
        if query:
            self.search_library_requested.emit(query)

    def _on_install_library_clicked(self):
        # Если выбрано в списке, берем оттуда, иначе из текстового поля
        current_item = self.results_list.currentItem()
        if current_item:
            library_name = current_item.data(Qt.UserRole)
        else:
            library_name = self.library_name_input.text().strip()
            
        if library_name:
            self.install_library_requested.emit(library_name)

    def _on_uninstall_clicked(self):
        current_item = self.installed_list.currentItem()
        if current_item:
            library_name = current_item.data(Qt.UserRole)
            reply = QMessageBox.question(self, "Удаление", f"Вы уверены, что хотите удалить библиотеку '{library_name}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.uninstall_library_requested.emit(library_name)
                # Удаляем из списка визуально сразу
                self.installed_list.takeItem(self.installed_list.row(current_item))

    def _on_tab_changed(self, index):
        # Если переключились на вкладку "Установленные" (индекс 1)
        if index == 1:
            self.list_installed_requested.emit()

    def _on_item_double_clicked(self, item):
        library_name = item.data(Qt.UserRole)
        self.install_library_requested.emit(library_name)

    def _on_install_zip_library_clicked(self):
        zip_file_path, _ = QFileDialog.getOpenFileName(self, "Выберите ZIP-архив библиотеки", "", "ZIP Files (*.zip);;All Files (*)")
        if zip_file_path:
            self.install_library_from_zip_requested.emit(zip_file_path)
            QMessageBox.information(self, "Установка библиотеки", 
                                    f"Запрос на установку библиотеки из ZIP-файла: {os.path.basename(zip_file_path)} отправлен. Проверьте терминал для статуса.")
