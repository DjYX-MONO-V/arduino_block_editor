# ui/block_canvas.py
import json
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QMenu, QApplication, QWidget
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QPoint, QMimeData, QRectF
from PyQt5.QtGui import QBrush, QPen, QColor, QPainter
from ui.block_widgets import FunctionBlockWidget
from core.block_data_models import FunctionBlockData, BlockProject # Будет определен позже

class BlockCanvas(QGraphicsView):
    blocks_changed = pyqtSignal() # Сигнал для оповещения об изменении блоков
    library_save_requested = pyqtSignal(object) # Проброс сигнала в MainWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.RubberBandDrag) # Для выделения нескольких блоков

        # Ограничиваем рабочую область, чтобы не "улетать" в бесконечность
        self.setSceneRect(-5000, -5000, 10000, 10000)

        self.blocks = [] # Список всех блоков на канвасе

        # Для перетаскивания фона
        self._pan_start_pos = QPointF()
        self._panning = False

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Отрисовывает сетку на фоне канваса."""
        super().drawBackground(painter, rect)

        # Цвет фона
        painter.fillRect(rect, QColor("#1E1E1E")) # Темный фон, как в VS Code

        # Параметры сетки
        grid_size_minor = 20  # Размер мелкой ячейки сетки
        grid_size_major = 100 # Размер крупной ячейки сетки (каждая 5-я мелкая)

        # Цвет мелкой сетки
        minor_grid_color = QColor("#2D2D2D") # Чуть светлее фона
        # Цвет крупной сетки
        major_grid_color = QColor("#3D3D3D") # Еще светлее

        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        # Отрисовка мелкой сетки
        painter.setPen(QPen(minor_grid_color, 0.5))
        for x in range(left - (left % grid_size_minor), right, grid_size_minor):
            painter.drawLine(x, top, x, bottom)
        for y in range(top - (top % grid_size_minor), bottom, grid_size_minor):
            painter.drawLine(left, y, right, y)

        # Отрисовка крупной сетки
        painter.setPen(QPen(major_grid_color, 1))
        for x in range(left - (left % grid_size_major), right, grid_size_major):
            painter.drawLine(x, top, x, bottom)
        for y in range(top - (top % grid_size_major), bottom, grid_size_major):
            painter.drawLine(left, y, right, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton: # Средняя кнопка мыши для панорамирования
            self._pan_start_pos = event.pos()
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        elif event.button() == Qt.LeftButton:
            # Проверяем, был ли клик по блоку
            item = self.itemAt(event.pos())
            if not item:
                # Если клик не по блоку, снимаем выделение со всех блоков
                for block in self.blocks:
                    block.setSelected(False)
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            # Вычисляем разницу между текущим и предыдущим положением мыши
            delta = event.pos() - self._pan_start_pos
            # Двигаем ползунки прокрутки на величину смещения
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = event.pos()
            return
        else:
            super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            try:
                data = json.loads(event.mimeData().text())
                if "id" in data: del data["id"]
                
                # Вычисляем позицию на сцене, куда бросили блок
                scene_pos = self.mapToScene(event.pos())
                data["pos_x"], data["pos_y"] = scene_pos.x(), scene_pos.y()
                
                block_data = FunctionBlockData.from_dict(data)
                block_widget = FunctionBlockWidget(block_data)
                block_widget.setPos(scene_pos)
                
                self.scene.addItem(block_widget)
                self.blocks.append(block_widget)
                block_widget.signals.block_data_changed.connect(self.blocks_changed.emit)
                block_widget.signals.request_deletion.connect(self._delete_block)
                block_widget.signals.request_library_save.connect(self.library_save_requested.emit)
                self.blocks_changed.emit()
                event.accept()
            except:
                event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
        elif event.button() == Qt.LeftButton:
            # После перемещения или выделения блоков, возможно, нужно обновить код
            self.blocks_changed.emit()
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Масштабирование
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        add_function_action = menu.addAction("Добавить функцию")
        # add_variable_action = menu.addAction("Добавить переменную") # Пример
        # add_if_action = menu.addAction("Добавить If-блок") # Пример

        action = menu.exec_(event.globalPos())

        if action == add_function_action:
            self._add_function_block(self.mapToScene(event.pos()))

    def _add_function_block(self, scene_pos: QPointF, name: str = None, description: str = None, code_content: str = None, block_type: str = "function"):
        # Создаем новую модель данных для блока
        if name is None:
            name = f"newFunction_{len(self.blocks)}"
        if description is None:
            description = "Описание новой функции"
        if code_content is None:
            code_content = "// Ваш код здесь"

        new_block_data = FunctionBlockData(
            name=name,
            description=description,
            code_content=code_content,
            pos_x=scene_pos.x(),
            pos_y=scene_pos.y(),
            block_type=block_type
        )
        # Создаем визуальный виджет блока
        block_widget = FunctionBlockWidget(new_block_data)
        block_widget.setPos(scene_pos)
        self.scene.addItem(block_widget)
        self.blocks.append(block_widget)
        block_widget.signals.block_data_changed.connect(self.blocks_changed.emit)
        block_widget.signals.request_deletion.connect(self._delete_block)
        block_widget.signals.request_library_save.connect(self.library_save_requested.emit)
        self.blocks_changed.emit() # Оповещаем об изменении
        return block_widget # Возвращаем созданный виджет

    def add_default_blocks(self):
        # Добавляем глобальный блок
        self._add_function_block(QPointF(50, 50), name="Global Includes & Variables", description="Здесь подключаются библиотеки и объявляются глобальные переменные", code_content="#include <Arduino.h>\n\n// Ваши глобальные переменные", block_type="global")
        # Добавляем setup()
        self._add_function_block(QPointF(50, 300), name="setup", description="Функция setup() выполняется один раз при запуске Arduino", code_content="Serial.begin(9600);", block_type="setup")
        # Добавляем loop()
        self._add_function_block(QPointF(50, 550), name="loop", description="Функция loop() выполняется постоянно после setup()", code_content="Serial.println(\"Hello from Arduino Block Editor!\");", block_type="loop")
        self.blocks_changed.emit()

    def clear_canvas(self):
        for block in self.blocks:
            self.scene.removeItem(block)
        self.blocks.clear()
        self.blocks_changed.emit()

    def load_project(self, project: BlockProject):
        self.clear_canvas()
        for block_data in project.function_blocks:
            block_widget = FunctionBlockWidget(block_data)
            block_widget.setPos(block_data.pos_x, block_data.pos_y)
            self.scene.addItem(block_widget)
            self.blocks.append(block_widget)
            block_widget.signals.block_data_changed.connect(self.blocks_changed.emit)
            block_widget.signals.request_deletion.connect(self._delete_block)
            block_widget.signals.request_library_save.connect(self.library_save_requested.emit)
        self.blocks_changed.emit()

    def _delete_block(self, block_widget):
        if block_widget in self.blocks:
            self.blocks.remove(block_widget)
            self.scene.removeItem(block_widget)
            self.blocks_changed.emit()

    def get_current_project_data(self) -> BlockProject:
        project = BlockProject()
        for block_widget in self.blocks:
            # Обновляем позицию блока в его модели данных перед сохранением
            block_widget.block_data.pos_x = block_widget.x()
            block_widget.block_data.pos_y = block_widget.y()
            project.add_function_block(block_widget.block_data)
        return project
