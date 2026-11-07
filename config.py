import os
import json
import tempfile
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Поддержка GOOGLE_CREDS_JSON из ENV (для Railway/Fly.io без файла в гите)
if creds_json := os.getenv("GOOGLE_CREDS_JSON"):
    try:
        creds_dict = json.loads(creds_json)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            os.environ["GOOGLE_SHEETS_CREDENTIALS"] = f.name
    except Exception as e:
        print(f"[WARNING] Ошибка загрузки Google creds из GOOGLE_CREDS_JSON: {e}")

@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
    SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
    SHEET_NAME: str = os.getenv("SHEET_NAME", "Sheet1")

    # Bot settings
    ADMIN_IDS: list[int] = None

    def __post_init__(self):
        if self.ADMIN_IDS is None:
            admin_str = os.getenv("ADMIN_IDS", "")
            self.ADMIN_IDS = [int(x) for x in admin_str.split(",") if x.strip()]

config = Config()