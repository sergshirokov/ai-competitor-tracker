"""
Конфигурация приложения
"""
import os
import logging
import sys
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

# === Настройка логирования ===
def setup_logging():
    """Настройка логирования для всего приложения"""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Основной логгер
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем логи от сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    return logging.getLogger("competitor_monitor")

# Инициализация логгера
logger = setup_logging()


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Нативный OpenAI (если задан — используется вместо ProxyAPI, без proxy_api_base_url)
    openai_key: str = os.getenv("OPENAI_KEY", "")
    # ProxyAPI (OpenAI-совместимый)
    proxy_api_key: str = os.getenv("PROXY_API_KEY", "")
    proxy_api_base_url: str = "https://api.proxyapi.ru/openai/v1"
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_vision_model: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # История
    history_file: str = "history.json"
    max_history_items: int = 10
    
    # Парсер (Playwright + stealth; после установки: playwright install chromium)
    # parser_timeout — ожидание body, локаторов и т.д.; первый запуск Chromium + медленный TLS
    # часто съедают секунды до goto, поэтому для навигации ниже отдельный лимит.
    parser_timeout: int = 30
    parser_navigation_timeout: int = 60
    parser_headless: bool = Field(default=True, description="Headless Chromium (False — меньше отпечаток headless, но нужен дисплей)")
    parser_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    parser_locale: str = "en-US"
    parser_timezone: str = "Europe/Moscow"
    parser_accept_language: str = "en-US,en;q=0.9"
    parser_navigator_languages: str = "en-US,en"
    parser_platform: str = "Win32"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

