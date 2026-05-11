# core/code_generator.py
from datetime import datetime
from collections import defaultdict
from core.block_data_models import BlockProject, FunctionBlockData

def generate_arduino_code(project: BlockProject, project_name: str = "sketch") -> dict:
    """
    Генерирует файлы Arduino проекта.
    Возвращает словарь {filename: code_content}
    """
    files = defaultdict(list)
    
    # Группируем блоки по файлам
    for block in project.function_blocks:
        # Если имя файла стандартное "sketch", заменяем его на имя проекта для совместимости с IDE
        name_part = block.file_name
        if name_part == "sketch":
            name_part = project_name
        fname = f"{name_part}{block.file_ext}"
        files[fname].append(block)

    generated_files = {}

    for filename, blocks in files.items():
        code_parts = []
        # Комментарий в стиле Arduino
        code_parts.append(f"// Arduino Block Editor - {filename}")

        if filename.endswith(".ino"):
            # Специфическая логика для главного файла
            global_content = ""
            setup_content = ""
            loop_content = ""
            funcs = []
            
            for b in blocks:
                if b.block_type == "global": global_content += b.code_content + "\n"
                elif b.block_type == "setup": setup_content += b.code_content + "\n"
                elif b.block_type == "loop": loop_content += b.code_content + "\n"
                else:
                    signature = b.name.strip()
                    if "(" not in signature: signature += "()"
                    if " " not in signature.split("(")[0]: signature = "void " + signature
                    funcs.append(f"{signature} {{\n{b.code_content}\n}}")
            
            if global_content: code_parts.append(global_content)
            code_parts.extend(funcs)
            code_parts.append(f"void setup() {{\n{setup_content}\n}}")
            code_parts.append(f"void loop() {{\n{loop_content}\n}}")
        else:
            # Для .h, .cpp, .c просто объединяем содержимое блоков
            # Добавляем Include Guard для заголовочных файлов
            if filename.endswith(".h"):
                guard = filename.replace(".", "_").upper() + "_INCLUDED"
                code_parts.append(f"#ifndef {guard}\n#define {guard}\n")
            
            for b in blocks:
                code_parts.append(f"// --- Block: {b.name} ---")
                code_parts.append(b.code_content + "\n")
                
            if filename.endswith(".h"):
                code_parts.append(f"#endif // {guard}")

        generated_files[filename] = "\n".join(code_parts)

    return generated_files
