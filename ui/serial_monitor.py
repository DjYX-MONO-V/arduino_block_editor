import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QComboBox, QLabel, QCheckBox)
from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QFont, QColor

class SerialReaderThread(QThread):
    """Поток для чтения данных из порта без блокировки UI."""
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.serial_port = None

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.1)
            while self.running:
                if self.serial_port.in_waiting > 0:
                    # Читаем данные и декодируем, игнорируя ошибки кодировки
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='replace')
                    self.data_received.emit(data)
                self.msleep(10)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def stop(self):
        self.running = False
        self.wait()

class SerialMonitorWindow(QWidget):
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.setWindowTitle(f"Монитор порта - {port}")
        self.resize(600, 400)
        self.setWindowFlags(Qt.Window) # Отдельное окно

        self._init_ui()
        self.reader_thread = None
        self.start_monitoring()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Верхняя панель управления
        top_layout = QHBoxLayout()
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["300", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "74880", "115200", "230400", "250000"])
        self.baud_combo.setCurrentText("9600")
        self.baud_combo.currentTextChanged.connect(self.restart_monitoring)
        
        self.clear_btn = QPushButton("Очистить")

        self.autoscroll_check = QCheckBox("Автопрокрутка")
        self.autoscroll_check.setChecked(True)

        top_layout.addWidget(QLabel("Скорость:"))
        top_layout.addWidget(self.baud_combo)
        top_layout.addStretch()
        top_layout.addWidget(self.autoscroll_check)
        top_layout.addWidget(self.clear_btn)
        layout.addLayout(top_layout)

        # Область вывода
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setStyleSheet("background-color: #1E1E1E; color: #00FF00; border: 1px solid #333;")
        layout.addWidget(self.output_area)
        
        self.clear_btn.clicked.connect(self.output_area.clear)

        # Панель отправки
        send_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите данные для отправки...")
        self.input_field.returnPressed.connect(self.send_data)
        
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_data)
        
        self.line_ending_combo = QComboBox()
        self.line_ending_combo.addItems(["Нет переноса", "NL (\\n)", "CR (\\r)", "Both (\\r\\n)"])
        self.line_ending_combo.setCurrentIndex(3)

        send_layout.addWidget(self.input_field)
        send_layout.addWidget(self.line_ending_combo)
        send_layout.addWidget(self.send_btn)
        layout.addLayout(send_layout)

    def start_monitoring(self):
        baud = int(self.baud_combo.currentText())
        self.reader_thread = SerialReaderThread(self.port, baud)
        self.reader_thread.data_received.connect(self.append_text)
        self.reader_thread.error_occurred.connect(self.handle_error)
        self.reader_thread.start()
        self.append_text(f"--- Порт {self.port} открыт на скорости {baud} ---\n", color="#FFFF00")

    def restart_monitoring(self):
        if self.reader_thread:
            self.reader_thread.stop()
        self.start_monitoring()

    def append_text(self, text, color=None):
        if color:
            self.output_area.setTextColor(QColor(color))
        else:
            self.output_area.setTextColor(QColor("#00FF00"))
            
        self.output_area.insertPlainText(text)
        
        if self.autoscroll_check.isChecked():
            self.output_area.verticalScrollBar().setValue(self.output_area.verticalScrollBar().maximum())

    def send_data(self):
        text = self.input_field.text()
        if not text or not self.reader_thread or not self.reader_thread.serial_port:
            return

        # Добавляем окончание строки
        ending = self.line_ending_combo.currentIndex()
        if ending == 1: text += "\n"
        elif ending == 2: text += "\r"
        elif ending == 3: text += "\r\n"

        try:
            self.reader_thread.serial_port.write(text.encode('utf-8'))
            self.input_field.clear()
        except Exception as e:
            self.append_text(f"\n Ошибка отправки: {e}\n", color="#FF0000")

    def handle_error(self, error_msg):
        self.append_text(f"\n Ошибка порта: {error_msg}\n", color="#FF0000")
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)

    def closeEvent(self, event):
        if self.reader_thread:
            self.reader_thread.stop()
        event.accept()