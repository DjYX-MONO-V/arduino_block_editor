# ui/calculator_window.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QGridLayout, QLabel, QComboBox, QCheckBox
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

class CalculatorWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Продвинутый калькулятор программиста")
        self.setMinimumSize(450, 550)
        self.setModal(False)  # Позволяет работать с редактором, не закрывая калькулятор
        
        self.current_base = 10
        self.word_size = 32
        self.is_signed = True
        self.result = 0
        self.expression = ""

        self._apply_dark_theme()
        self._init_ui()

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #1E1E1E; color: #D4D4D4; }
            QLineEdit { 
                background-color: #3C3C3C; color: #D4D4D4; border: 1px solid #454545; 
                padding: 10px; font-size: 22px; font-family: 'Consolas'; 
            }
            QPushButton { 
                background-color: #333333; color: #D4D4D4; border: 1px solid #454545; 
                padding: 10px; font-size: 13px; min-width: 45px; font-family: 'Consolas';
            }
            QPushButton:hover { background-color: #454545; }
            QPushButton:pressed { background-color: #094771; }
            QLabel { color: #858585; font-size: 11px; font-family: 'Consolas'; }
            QComboBox { background-color: #3C3C3C; color: #D4D4D4; border: 1px solid #454545; padding: 2px; }
            QCheckBox { color: #D4D4D4; }
        """)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Дисплей
        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.display)

        # Информационные метки (Конвертация в реальном времени)
        self.info_layout = QVBoxLayout()
        self.hex_label = QLabel("HEX: 0")
        self.dec_label = QLabel("DEC: 0")
        self.oct_label = QLabel("OCT: 0")
        self.bin_label = QLabel("BIN: 0")
        for lbl in [self.hex_label, self.dec_label, self.oct_label, self.bin_label]:
            self.info_layout.addWidget(lbl)
        main_layout.addLayout(self.info_layout)

        # Настройки режима
        settings_layout = QHBoxLayout()
        
        self.base_combo = QComboBox()
        self.base_combo.addItems(["HEX", "DEC", "OCT", "BIN"])
        self.base_combo.setCurrentText("DEC")
        self.base_combo.currentTextChanged.connect(self._on_base_changed)

        self.word_combo = QComboBox()
        self.word_combo.addItems(["8-bit", "16-bit", "32-bit", "64-bit"])
        self.word_combo.setCurrentText("32-bit")
        self.word_combo.currentTextChanged.connect(self._on_word_size_changed)

        self.signed_check = QCheckBox("Signed")
        self.signed_check.setChecked(True)
        self.signed_check.stateChanged.connect(self._on_signed_changed)

        settings_layout.addWidget(QLabel("Base:"))
        settings_layout.addWidget(self.base_combo)
        settings_layout.addWidget(QLabel("Word:"))
        settings_layout.addWidget(self.word_combo)
        settings_layout.addWidget(self.signed_check)
        main_layout.addLayout(settings_layout)

        # Сетка кнопок
        grid = QGridLayout()
        buttons = [
            ('A', 0, 0), ('B', 0, 1), ('C', 0, 2), ('D', 0, 3), ('E', 0, 4), ('F', 0, 5),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('(', 1, 3), (')', 1, 4), ('CE', 1, 5),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3), ('/', 2, 4), ('CLR', 2, 5),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3), ('-', 3, 4), ('=', 3, 5),
            ('0', 4, 0), ('AND', 4, 1), ('OR', 4, 2), ('XOR', 4, 3), ('NOT', 4, 4), ('<<', 4, 5),
            ('>>', 5, 0), ('%', 5, 1), ('&', 5, 2), ('|', 5, 3), ('^', 5, 4), ('~', 5, 5)
        ]

        self.btn_map = {}
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(lambda ch, t=text: self._on_button_click(t))
            grid.addWidget(btn, row, col)
            self.btn_map[text] = btn

        main_layout.addLayout(grid)
        self._update_button_states()

    def _on_base_changed(self, base_str):
        bases = {"HEX": 16, "DEC": 10, "OCT": 8, "BIN": 2}
        self.current_base = bases[base_str]
        self._update_button_states()
        self._update_display()

    def _on_word_size_changed(self, size_str):
        self.word_size = int(size_str.split('-')[0])
        self._apply_constraints()
        self._update_display()

    def _on_signed_changed(self, state):
        self.is_signed = (state == Qt.Checked)
        self._apply_constraints()
        self._update_display()

    def _update_button_states(self):
        """Включает/выключает кнопки в зависимости от системы счисления."""
        hex_digits = "ABCDEF"
        dec_digits = "89"
        oct_digits = "234567"
        
        for char in hex_digits:
            self.btn_map[char].setEnabled(self.current_base == 16)
        for char in dec_digits:
            self.btn_map[char].setEnabled(self.current_base > 8)
        for char in oct_digits:
            self.btn_map[char].setEnabled(self.current_base > 2)

    def _on_button_click(self, text):
        if text == 'CLR':
            self.expression = ""
            self.result = 0
        elif text == 'CE':
            self.expression = self.expression[:-1]
        elif text == '=':
            self._evaluate()
        else:
            # Заменяем текстовые операторы на символы Python
            op_map = {'AND': '&', 'OR': '|', 'XOR': '^', 'NOT': '~'}
            self.expression += op_map.get(text, text)
        
        self.display.setText(self.expression if self.expression else "0")

    def _evaluate(self):
        try:
            # Для простоты используем eval (в данном контексте безопасно)
            # Примечание: предполагается ввод в десятичной системе для вычислений
            self.result = int(eval(self.display.text()))
            self._apply_constraints()
            self.expression = str(self.result)
            self._update_display()
        except Exception:
            self.display.setText("Error")
            self.expression = ""

    def _apply_constraints(self):
        """Ограничивает число согласно выбранной разрядности (overflow)."""
        mask = (1 << self.word_size) - 1
        self.result &= mask
        if self.is_signed:
            if self.result & (1 << (self.word_size - 1)):
                self.result -= (1 << self.word_size)

    def _update_display(self):
        val = int(self.result)
        u_val = val & ((1 << self.word_size) - 1) # Unsigned версия для HEX/BIN
        
        # Обновляем инфо-метки
        self.hex_label.setText(f"HEX: {hex(u_val).upper()[2:]}")
        self.dec_label.setText(f"DEC: {val}")
        self.oct_label.setText(f"OCT: {oct(u_val)[2:]}")
        self.bin_label.setText(f"BIN: {bin(u_val)[2:]}")

        # Обновляем главный дисплей согласно текущей базе
        if self.current_base == 16:
            self.display.setText(hex(u_val).upper()[2:])
        elif self.current_base == 10:
            self.display.setText(str(val))
        elif self.current_base == 8:
            self.display.setText(oct(u_val)[2:])
        elif self.current_base == 2:
            self.display.setText(bin(u_val)[2:])