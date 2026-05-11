# Arduino Block Editor (v0.0.22)

**Arduino Block Editor** — это специализированная среда разработки (IDE) для контроллеров Arduino, совмещающая визуальное редактирование блоков и написание кода.

> **Скачать готовую версию (.exe):** [Перейти к релизам](https://github.com/DjYX-MONO-V/arduino_block_editor/releases)

![Arduino Block Editor Screenshot](screenshot_v0.0.22.png)

## Основные возможности
* **Визуальный холст:** Drag-and-drop блоков, масштабирование и сетка.
* **Генератор кода:** Автоматическое преобразование блоков в `.ino`, `.h` и `.cpp` файлы.
* **Совместимость с Arduino IDE:** Проекты сохраняются в структуру папок, которую можно открыть в стандартной среде Arduino.
* **Редактор кода:** Подсветка синтаксиса, нумерация строк и поиск (Ctrl+F).
* **Интеграция с Arduino CLI:** Компиляция и прошивка прямо из приложения.
* **Инструменты:** Продвинутый калькулятор программиста и встроенный PDF-просмотрщик документации.
* **Монитор порта:** Встроенный Serial Monitor для отладки.

## Как запустить из исходников

1. Установите Python 3.8+
2. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/DjYX-MONO-V/arduino_block_editor.git
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Запустите:
   ```bash
   python main.py
   ```

## Сборка в EXE
Для сборки использовался PyInstaller:
```bash
pyinstaller --noconsole --onedir ^
    --paths "Libs" ^
    --icon="icon.ico" ^
    --name="ArduinoBlockEditor" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-data "Libs;Libs" ^
    main.py
```

## Требования
Для работы компиляции и загрузки необходимо наличие установленного Arduino IDE (или `arduino-cli`).

## Лицензия
MIT