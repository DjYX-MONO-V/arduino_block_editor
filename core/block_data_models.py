# core/block_data_models.py
import json

class FunctionBlockData:
    def __init__(self, name: str, description: str, code_content: str, pos_x: float = 0, pos_y: float = 0, block_id: str = None, block_type: str = "function", color: str = "#2D2D30", width: float = 300, height: float = 250):
        self.id = block_id if block_id else self._generate_id()
        self.name = name
        self.description = description
        self.code_content = code_content
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.block_type = block_type # "function", "setup", "loop", "global"
        self.color = color
        self.width = width
        self.height = height
        # Можно добавить другие свойства, например, цвет, входные/выходные порты и т.д.

    def _generate_id(self):
        import uuid
        return str(uuid.uuid4())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "code_content": self.code_content,
            "pos_x": round(self.pos_x, 2), # Округляем для более чистого JSON
            "pos_y": round(self.pos_y, 2), # Округляем для более чистого JSON
            "block_type": self.block_type,
            "color": self.color,
            "width": self.width,
            "height": self.height
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            block_id=data.get("id"),
            name=data.get("name", "Unnamed Function"),
            description=data.get("description", ""),
            code_content=data.get("code_content", ""),
            pos_x=float(data.get("pos_x", 0)),
            pos_y=float(data.get("pos_y", 0)),
            block_type=data.get("block_type", "function"),
            color=data.get("color", "#2D2D30"),
            width=float(data.get("width", 300)),
            height=float(data.get("height", 250))
        )

class BlockProject:
    def __init__(self):
        self.function_blocks: list[FunctionBlockData] = []
        # Можно добавить другие типы блоков, глобальные переменные и т.д.

    def add_function_block(self, block: FunctionBlockData):
        self.function_blocks.append(block)

    def to_dict(self):
        return {
            "version": "1.0",
            "function_blocks": [block.to_dict() for block in self.function_blocks]
        }

    def save_to_file(self, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        project = cls()
        for block_data_dict in data.get("function_blocks", []):
            project.add_function_block(FunctionBlockData.from_dict(block_data_dict))
        return project
