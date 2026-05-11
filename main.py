# main.py
import sys
import os

# Явно импортируем serial здесь. Даже если мы его не используем в этом файле,
# это заставит PyInstaller включить библиотеку в сборку.
try:
    import serial
except ImportError:
    pass

# Подавляем лишние логи Chromium (Assertion failed и прочие), 
# устанавливая уровень логирования на 3 (только фатальные ошибки).
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--log-level=3 --disable-logging"

# Добавляем папку libs в пути поиска модулей, чтобы можно было импортировать 
# библиотеки, установленные локально в папку проекта.
current_dir = os.path.dirname(os.path.abspath(__file__))
libs_path = os.path.join(current_dir, 'Libs')

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# Эта часть нужна только при разработке. При запуске в EXE PyInstaller сам упаковывает зависимости.
if not getattr(sys, 'frozen', False):
    # Пытаемся найти папку .venv в корневой директории проекта
    local_venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".venv", "Lib", "site-packages")
    if os.path.exists(local_venv) and local_venv not in sys.path:
        sys.path.append(local_venv)

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized() # Или show() для обычного размера
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
