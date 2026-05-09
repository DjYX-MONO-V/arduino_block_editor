# core/settings_manager.py
import os
import json

class SettingsManager:
    def __init__(self):
        # Файл настроек будет храниться в домашней директории пользователя
        self.settings_file = os.path.join(os.path.expanduser("~"), "arduino_block_editor_settings.json")
        self.settings = self._load_settings()

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # Если файл поврежден, возвращаем пустые настройки
                return {}
        return {}

    def _save_settings(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self._save_settings()