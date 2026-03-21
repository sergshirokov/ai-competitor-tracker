"""
Скрипт запуска приложения Мониторинг конкурентов
"""
import uvicorn
import logging
from backend.config import settings, logger

# Настраиваем уровень логирования
logging.getLogger("competitor_monitor").setLevel(logging.INFO)

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("🚀 МОНИТОРИНГ КОНКУРЕНТОВ - AI Ассистент")
    print("=" * 60)
    print()
    print(f"📍 Веб-интерфейс:  http://localhost:{settings.api_port}")
    print(f"📚 Документация:   http://localhost:{settings.api_port}/docs")
    print(f"📖 ReDoc:          http://localhost:{settings.api_port}/redoc")
    print()
    print(f"🤖 Модель текста:  {settings.openai_model}")
    print(f"👁️ Модель vision:  {settings.openai_vision_model}")
    _key_ok = bool((settings.openai_key or "").strip() or settings.proxy_api_key)
    print(f"🔑 API ключ:       {'✓ Настроен' if _key_ok else '✗ НЕ ЗАДАН!'}")
    print()
    print("-" * 60)
    print("Логи запросов будут отображаться ниже...")
    print("-" * 60)
    print()
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
