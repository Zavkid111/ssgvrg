import os

# Переменные будут автоматически подтягиваться из панели Bothost
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))  # если несколько ID через запятую
DB_PATH = "database/database.db"

DEFAULT_REQUISITES = """
Сбербанк
2202208214031917
Завкиддин А.
"""
