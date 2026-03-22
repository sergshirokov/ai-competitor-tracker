# Мониторинг конкурентов — AI-ассистент

MVP для анализа конкурентной среды: текст, изображения и парсинг сайтов с анализом через OpenAI (включая vision по скриншоту страницы). Есть веб-интерфейс и опциональный десктоп-клиент; массовый парсинг из консоли описан ниже в разделе **Описание**.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-API-purple.svg)

## Описание

Приложение позволяет:

- **Анализировать текст конкурентов** — структурированная аналитика: сильные и слабые стороны, уникальные предложения, рекомендации, резюме.
- **Анализировать изображения** — описание, маркетинговые инсайты, оценка визуального стиля (0–10), рекомендации.
- **Парсить сайты по URL** — извлечение title, H1, первого абзаца, **скриншота viewport** через **Playwright (Chromium)** с **playwright-stealth**; далее анализ через **Vision API** (скриншот + контекст) или текстовый fallback, если скриншот недоступен.
- **Вести историю** — последние **N** запросов (по умолчанию 10) в JSON-файле; для типа **parse** сохраняется отдельный **снимок анализа** (`ParseHistorySnapshot`), не привязанный напрямую к DTO ответа LLM.

### Веб-интерфейс (frontend)

- Вкладка **История**: список записей; для записей типа **parse**, у которых есть сохранённый анализ, по **клику** открывается **модальное окно** с полным текстом сохранённого `parse_analysis` (тот же вид блоков, что и в основном результате анализа).

### Десктоп-клиент

- В каталоге `desktop/` — PyQt-приложение (см. `desktop/README.md`). На текущем этапе расширенное отображение истории parse в UI **не дублирует** веб-модалку; при необходимости это можно добавить позже.

### Консольный batch-парсинг (`parsedemo`)

- Скрипт в каталоге `parsedemo/` последовательно вызывает **`POST /parse_demo`** для списка URL из JSON (форматы — в `parsedemo/urls.example.json` и в комментариях в `parsedemo/main.py`).
- Требуется **уже запущенный** backend (`python run.py` или uvicorn).

```bash
python parsedemo/main.py
python parsedemo/main.py --file parsedemo/urls.json --base-url http://localhost:8000
```

## Быстрый старт

### 1. Клонирование и зависимости

```bash
cd ai-competitor-tracker

python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

Без установки браузера Chromium команды Playwright для парсинга не заработают.

### 2. Переменные окружения

Создайте `.env` в корне (шаблон — `env.example.txt`):

| Переменная | Назначение |
|------------|------------|
| `OPENAI_KEY` | Ключ **нативного** OpenAI (`api.openai.com`). Если задан — используется он. |
| `PROXY_API_KEY` | Ключ [ProxyAPI](https://proxyapi.ru/) (OpenAI-совместимый endpoint), если `OPENAI_KEY` не задан. |
| `OPENAI_MODEL` | Модель для текста (по умолчанию `gpt-4o-mini`). |
| `OPENAI_VISION_MODEL` | Модель для vision (по умолчанию `gpt-4o-mini`). |
| `API_HOST`, `API_PORT` | Хост и порт сервера (по умолчанию `0.0.0.0`, `8000`). |

Опционально для парсера (таймауты, headless, fingerprint): см. комментарии в `env.example.txt` и поля в `backend/config.py` (`PARSER_*`).

### 3. Запуск

Рекомендуемый способ (логи в консоли, reload, на **Windows** выставлен **Proactor** event loop для совместимости с Playwright):

```bash
python run.py
```

Альтернатива:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Веб-UI: `http://localhost:8000` (статика и API с одного процесса).

## Структура проекта

```
ai-competitor-tracker/
├── backend/
│   ├── main.py                 # FastAPI: маршруты, раздача frontend, CORS
│   ├── config.py               # Настройки (OpenAI/ProxyAPI, парсер, история)
│   ├── models/
│   │   └── schemas.py          # Pydantic: запросы/ответы, CompetitorAnalysis, ParseHistorySnapshot, HistoryItem
│   └── services/
│       ├── openai_service.py   # Вызовы OpenAI (текст, изображение, скриншот сайта)
│       ├── parser_service.py   # Playwright + stealth, извлечение данных и скриншота
│       └── history_service.py  # Чтение/запись history.json
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js                  # Вкладки, API, результаты, история, модалка parse
├── desktop/                    # Опциональный PyQt-клиент (сборка см. desktop/README.md)
├── parsedemo/                  # Скрипт batch-вызова POST /parse_demo по списку URL
│   ├── main.py
│   └── urls.example.json
├── run.py                      # Точка входа uvicorn + подсказки в консоли
├── requirements.txt
├── env.example.txt
├── history.json                # История (создаётся при первой записи)
├── docs.md                     # Подробности по API
└── README.md
```

## Функциональность API (кратко)

### `POST /analyze_text`

Текст конкурента (минимум 10 символов) → `CompetitorAnalysis` (сильные/слабые стороны, предложения, рекомендации, резюме).

### `POST /analyze_image`

Файл изображения → `ImageAnalysis`.

### `POST /parse_demo`

URL → парсинг страницы (Playwright), при успехе — `ParsedContent` с полями страницы и `analysis: CompetitorAnalysis`. Для анализа по скриншоту в структуру могут попадать поля **готовности контента к обучению LLM** (`ai_compliance_score`, `ai_training_recommendations`).

### `GET /history` / `DELETE /history`

Список записей истории; в элементах с `request_type: "parse"` может быть поле **`parse_analysis`** — это **`ParseHistorySnapshot`** (снимок на момент сохранения), сериализованный в JSON под тем же ключом, что и раньше.

### История и снимок parse

- При успешном `parse_demo` в историю пишется не сырой ответ LLM как «истина навсегда», а **`ParseHistorySnapshot.from_competitor_analysis(analysis)`** — явное отображение `CompetitorAnalysis` → модель хранения.
- Файл и лимит: `history.json`, `max_history_items` (по умолчанию 10) в `backend/config.py`.

## Технологии

- **Backend:** FastAPI, Python 3.9+, Pydantic v2, Uvicorn  
- **AI:** OpenAI Python SDK; поддержка нативного API и ProxyAPI  
- **Парсинг:** Playwright (Chromium), playwright-stealth; синхронный движок в отдельном потоке (`asyncio.to_thread`) для стабильности с async-приложением  
- **Frontend:** HTML/CSS/vanilla JS  
- **Прочее:** Pillow (изображения), python-dotenv, pydantic-settings  

## Документация API

После запуска сервера:

- Swagger UI: `http://localhost:8000/docs`  
- ReDoc: `http://localhost:8000/redoc`  

Дополнительно: [docs.md](docs.md).

## Требования

- Python 3.9+  
- Ключ OpenAI или ProxyAPI с доступом к выбранным моделям  
- Установленный **Chromium для Playwright** (`playwright install chromium`)  
- Сеть для API и загрузки страниц  

## Лицензия

MIT License
