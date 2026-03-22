# Документация API — Мониторинг конкурентов

## Содержание

1. [Структура проекта](#структура-проекта)
2. [Описание API](#описание-api)
3. [Примеры запросов](#примеры-запросов)
4. [Мультимодальные функции](#мультимодальные-функции)
5. [Модели данных](#модели-данных)
6. [Коды ошибок](#коды-ошибок)
7. [Конфигурация](#конфигурация)
8. [Безопасность](#безопасность)

---

## Структура проекта

```
ai-competitor-tracker/
├── backend/
│   ├── main.py                  # FastAPI: маршруты, статика frontend
│   ├── config.py                # OpenAI/ProxyAPI, парсер, история
│   ├── models/
│   │   └── schemas.py           # Pydantic: запросы/ответы, ParseHistorySnapshot
│   └── services/
│       ├── openai_service.py    # OpenAI: текст, изображение, скриншот сайта
│       ├── parser_service.py    # Playwright (Chromium) + stealth, скриншот viewport
│       └── history_service.py   # history.json
├── frontend/                    # Веб-UI (vanilla JS)
├── desktop/                     # Опциональный PyQt-клиент
├── parsedemo/                   # Batch-вызовы POST /parse_demo по списку URL
├── run.py                       # Запуск uvicorn (рекомендуется)
├── requirements.txt
├── env.example.txt
├── history.json
├── README.md
└── docs.md
```

---

## Описание API

### Базовый URL

```
http://localhost:8000
```

Порт задаётся переменной `API_PORT` (по умолчанию `8000`).

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Главная страница (веб-интерфейс) |
| POST | `/analyze_text` | Анализ текста конкурента |
| POST | `/analyze_image` | Анализ изображения конкурента |
| POST | `/parse_demo` | Парсинг сайта по URL (Playwright) и анализ (vision по скриншоту или текстовый fallback) |
| GET | `/history` | История запросов |
| DELETE | `/history` | Очистка истории |
| GET | `/health` | Проверка работоспособности |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

## Примеры запросов

### 1. Анализ текста (`POST /analyze_text`)

**Запрос:**

```bash
curl -X POST "http://localhost:8000/analyze_text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Наша компания предлагает уникальные решения для бизнеса. Мы работаем на рынке 10 лет и обслуживаем более 1000 клиентов. Наши преимущества: быстрая доставка, гарантия качества, индивидуальный подход к каждому клиенту."
  }'
```

**Ответ:** поле `analysis` соответствует модели `CompetitorAnalysis` (см. [ниже](#competitoranalysis)). Для чисто текстового анализа поля `ai_compliance_score` и `ai_training_recommendations` обычно `null` и `[]`.

```json
{
  "success": true,
  "analysis": {
    "strengths": [
      "Долгий опыт работы на рынке (10 лет)",
      "Большая клиентская база (1000+ клиентов)",
      "Комплексный подход к обслуживанию"
    ],
    "weaknesses": [
      "Отсутствие конкретных цен",
      "Нет упоминания о технологиях",
      "Общие формулировки без специфики"
    ],
    "unique_offers": [
      "Индивидуальный подход к каждому клиенту",
      "Гарантия качества"
    ],
    "recommendations": [
      "Добавить конкретные цифры и кейсы",
      "Указать уникальные технологические преимущества",
      "Включить отзывы клиентов"
    ],
    "summary": "Компания позиционирует себя как надёжного партнёра с опытом, но маркетинговые материалы требуют конкретизации для повышения конверсии.",
    "ai_compliance_score": null,
    "ai_training_recommendations": []
  },
  "error": null
}
```

### 2. Анализ изображения (`POST /analyze_image`)

**Запрос:**

```bash
curl -X POST "http://localhost:8000/analyze_image" \
  -F "file=@banner.jpg"
```

**Ответ:**

```json
{
  "success": true,
  "analysis": {
    "description": "Рекламный баннер с изображением продукта на синем градиентном фоне. Крупный заголовок белым шрифтом, кнопка CTA оранжевого цвета.",
    "marketing_insights": [
      "Чёткая визуальная иерархия привлекает внимание",
      "Контрастная цветовая схема выделяет CTA",
      "Минималистичный дизайн не перегружает восприятие"
    ],
    "visual_style_score": 7,
    "visual_style_analysis": "Современный корпоративный стиль с хорошим балансом элементов. Типографика читабельна, но можно улучшить отступы.",
    "recommendations": [
      "Добавить социальное доказательство (отзывы, рейтинги)",
      "Увеличить размер CTA кнопки",
      "Рассмотреть A/B тестирование цветов"
    ]
  },
  "error": null
}
```

### 3. Парсинг сайта (`POST /parse_demo`)

Страница загружается в **Chromium** через **Playwright** (со stealth-скриптами), извлекаются title, H1, первый абзац; делается **скриншот viewport**. Анализ: при наличии скриншота — **Vision API** с контекстом URL и текста; иначе — текстовый анализ по извлечённым полям. В ответе `data.analysis` — `CompetitorAnalysis`; для сценария со скриншотом часто заполняются `ai_compliance_score` (0–10) и `ai_training_recommendations`.

**Запрос:**

```bash
curl -X POST "http://localhost:8000/parse_demo" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Ответ (иллюстративный; фактический текст анализа зависит от модели и страницы):**

```json
{
  "success": true,
  "data": {
    "url": "https://example.com",
    "title": "Example Domain",
    "h1": "Example Domain",
    "first_paragraph": "This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
    "analysis": {
      "strengths": [
        "Страница быстро загружается и не перегружена контентом",
        "Заголовок H1 совпадает с темой и сразу объясняет назначение страницы",
        "Текст явно описывает, что домен можно использовать в примерах без согласования"
      ],
      "weaknesses": [
        "Нет навигации, брендинга и призыва к действию — страница выглядит как заглушка",
        "Отсутствуют контакты, политика и другие элементы доверия",
        "Мало материала для оценки маркетинговой подачи или УТП"
      ],
      "unique_offers": [
        "Домен зарезервирован IANA для документации и примеров — это редкий случай «официальной» заглушки"
      ],
      "recommendations": [
        "Если это продуктовый сайт, добавить структуру разделов и ценностное предложение",
        "Для обучающих материалов — усилить пояснение сценариев использования домена",
        "Добавить ссылки на справку или политику, если страница станет публичной точкой входа"
      ],
      "summary": "Страница example.com — минималистичная служебная заглушка с понятным текстом о допустимом использовании домена в документах; с точки зрения конкурентного анализа это не типичный коммерческий лендинг, а справочный пример.",
      "ai_compliance_score": 5,
      "ai_training_recommendations": [
        "Добавить размеченные блоки (FAQ, how-to) для обучения на структурированных парах вопрос–ответ",
        "Вынести ключевые формулировки в короткие абзацы с явными заголовками",
        "Избегать дублирования одной мысли в title, H1 и первом абзаце без новой информации"
      ]
    },
    "error": null
  },
  "error": null
}
```

### 4. Получение истории (`GET /history`)

Для записей с `request_type: "parse"` в теле может быть **`parse_analysis`** — снимок типа **`ParseHistorySnapshot`** (сохраняется при успешном `parse_demo`, отдельно от «живого» DTO ответа LLM).

**Запрос:**

```bash
curl -X GET "http://localhost:8000/history"
```

**Ответ (пример с записью parse и текстовой записью):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-15T10:30:00",
      "request_type": "parse",
      "request_summary": "URL: https://example.com",
      "response_summary": "Страница example.com — минималистичная служебная заглушка с понятным текстом о допустимом использовании домена в документах; с точки зрения конкурентного анализа это не типичный коммерческий лендинг, а справочный пример.",
      "parse_analysis": {
        "strengths": [
          "Страница быстро загружается и не перегружена контентом",
          "Заголовок H1 совпадает с темой и сразу объясняет назначение страницы",
          "Текст явно описывает, что домен можно использовать в примерах без согласования"
        ],
        "weaknesses": [
          "Нет навигации, брендинга и призыва к действию — страница выглядит как заглушка",
          "Отсутствуют контакты, политика и другие элементы доверия",
          "Мало материала для оценки маркетинговой подачи или УТП"
        ],
        "unique_offers": [
          "Домен зарезервирован IANA для документации и примеров — это редкий случай «официальной» заглушки"
        ],
        "recommendations": [
          "Если это продуктовый сайт, добавить структуру разделов и ценностное предложение",
          "Для обучающих материалов — усилить пояснение сценариев использования домена",
          "Добавить ссылки на справку или политику, если страница станет публичной точкой входа"
        ],
        "summary": "Страница example.com — минималистичная служебная заглушка с понятным текстом о допустимом использовании домена в документах; с точки зрения конкурентного анализа это не типичный коммерческий лендинг, а справочный пример.",
        "ai_compliance_score": 5,
        "ai_training_recommendations": [
          "Добавить размеченные блоки (FAQ, how-to) для обучения на структурированных парах вопрос–ответ",
          "Вынести ключевые формулировки в короткие абзацы с явными заголовками",
          "Избегать дублирования одной мысли в title, H1 и первом абзаце без новой информации"
        ]
      }
    },
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "timestamp": "2024-01-15T09:00:00",
      "request_type": "text",
      "request_summary": "Наша компания предлагает уникальные решения для бизнеса. Мы работаем на рынке 10 лет и обслуживаем более 1000 клиентов. Наши преимущества: быстрая доставка, гарантия качества, индивидуальный подход к каждому клиенту.",
      "response_summary": "Компания позиционирует себя как надёжного партнёра с опытом, но маркетинговые материалы требуют конкретизации для повышения конверсии.",
      "parse_analysis": null
    }
  ],
  "total": 2
}
```

Записи без сохранённого анализа parse или старые записи могут иметь `parse_analysis: null`.

### 5. Очистка истории (`DELETE /history`)

**Запрос:**

```bash
curl -X DELETE "http://localhost:8000/history"
```

**Ответ:**

```json
{
  "success": true,
  "message": "История очищена"
}
```

### 6. Проверка здоровья (`GET /health`)

**Запрос:**

```bash
curl -X GET "http://localhost:8000/health"
```

**Ответ:**

```json
{
  "status": "healthy",
  "service": "Competitor Monitor",
  "version": "1.0.0"
}
```

---

## Мультимодальные функции

### Текст

Подходит контент с сайтов конкурентов, рекламы, описаний продуктов и т.п.

**Минимальная длина:** 10 символов (`TextAnalysisRequest`).

### Изображения

Форматы: JPEG, PNG, GIF, WebP. Разумный размер файла — до нескольких мегабайт (см. ограничения в `backend/main.py` при необходимости).

### Парсинг веб-страниц

- **Движок:** Playwright, браузер **Chromium** (после `pip install` нужен `playwright install chromium`).
- **Stealth:** снижение признаков автоматизации (`playwright-stealth`), настраиваемые User-Agent, locale, timezone и др. через `backend/config.py` / переменные `PARSER_*`.
- **Извлечение:** title, H1, первый значимый абзац; **скриншот** видимой области страницы для vision-анализа.
- **Протокол:** при отсутствии схемы в запросе backend может дописать `https://` (см. логику в API).
- **Таймауты:** `PARSER_TIMEOUT` (операции на странице), `PARSER_NAVIGATION_TIMEOUT` (навигация `goto`) — см. `env.example.txt`.

Массовый прогон URL из консоли: каталог `parsedemo/` (скрипт вызывает `POST /parse_demo` для каждого URL).

---

## Модели данных

### TextAnalysisRequest

```typescript
{
  text: string  // минимум 10 символов
}
```

### ParseDemoRequest

```typescript
{
  url: string
}
```

### CompetitorAnalysis

Структурированный анализ в ответах API (`/analyze_text`, `data.analysis` в `/parse_demo`).

```typescript
{
  strengths: string[]
  weaknesses: string[]
  unique_offers: string[]
  recommendations: string[]
  summary: string
  ai_compliance_score: number | null   // 0–10; типично для анализа по скриншоту сайта
  ai_training_recommendations: string[]
}
```

### ParseHistorySnapshot

Снимок для **хранения в истории** по операциям parse. Структура сознательно совпадает с полезной нагрузкой анализа, но это **отдельная** модель: изменения в `CompetitorAnalysis` не меняют историю без явного маппинга (`from_competitor_analysis`). В JSON ответа `GET /history` поле по-прежнему называется **`parse_analysis`**.

```typescript
{
  strengths: string[]
  weaknesses: string[]
  unique_offers: string[]
  recommendations: string[]
  summary: string
  ai_compliance_score: number | null
  ai_training_recommendations: string[]
}
```

### ImageAnalysis

```typescript
{
  description: string
  marketing_insights: string[]
  visual_style_score: number    // 0–10
  visual_style_analysis: string
  recommendations: string[]
}
```

### HistoryItem

```typescript
{
  id: string
  timestamp: string             // ISO 8601
  request_type: "text" | "image" | "parse"
  request_summary: string
  response_summary: string
  parse_analysis: ParseHistorySnapshot | null  // только для parse, если сохранён снимок
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Некорректный запрос |
| 422 | Ошибка валидации (Pydantic) |
| 500 | Внутренняя ошибка сервера |

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENAI_KEY` | Ключ нативного OpenAI (`api.openai.com`). Если задан, используется вместо ProxyAPI. | — |
| `PROXY_API_KEY` | Ключ [ProxyAPI](https://proxyapi.ru/) (OpenAI-совместимый endpoint) | — |
| `OPENAI_MODEL` | Модель для текста | `gpt-4o-mini` |
| `OPENAI_VISION_MODEL` | Модель для vision | `gpt-4o-mini` |
| `API_HOST` | Хост сервера | `0.0.0.0` |
| `API_PORT` | Порт сервера | `8000` |
| `PARSER_TIMEOUT` | Таймаут операций на странице (сек.) | `30` |
| `PARSER_NAVIGATION_TIMEOUT` | Таймаут `page.goto` (сек.) | `60` |
| `PARSER_HEADLESS` | Headless Chromium | `true` |

Полный список опций парсера (User-Agent, locale, timezone и т.д.) — в `env.example.txt` и `backend/config.py`.

### OpenAI и ProxyAPI

- При наличии **`OPENAI_KEY`** запросы идут в официальный API OpenAI.
- Иначе используется **`PROXY_API_KEY`** и базовый URL ProxyAPI из конфигурации.

### История

- Максимум записей настраивается (`max_history_items` в коде, по умолчанию **10**).
- Файл: **`history.json`**, кодировка UTF-8.

---

## Безопасность

- Не храните API-ключи в коде; используйте `.env`.
- Добавьте `.env` в `.gitignore`.
- В продакшене используйте HTTPS и ограничьте CORS под ваши домены.
