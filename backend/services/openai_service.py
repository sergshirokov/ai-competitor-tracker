"""
Сервис для работы с OpenAI API или ProxyAPI (OpenAI-совместимый).
ProxyAPI: https://proxyapi.ru/docs/openai-text-generation
Responses API (vision): https://proxyapi.ru/docs/openai-vision
"""
import json
import re
import time
import logging
from typing import Optional

from openai import OpenAI

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

# Логгер для сервиса
logger = logging.getLogger("competitor_monitor.openai")


class OpenAIService:
    """Сервис анализа через нативный OpenAI API или ProxyAPI."""
    
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация OpenAI сервиса")
        logger.info(f"  Модель текста: {settings.openai_model}")
        logger.info(f"  Модель vision: {settings.openai_vision_model}")

        openai_key = (settings.openai_key or "").strip()
        if openai_key:
            logger.info("  Режим: OpenAI API (api.openai.com)")
            logger.info(f"  API ключ: {'*' * 10}...{openai_key[-4:]}")
            self.client = OpenAI(api_key=openai_key)
        else:
            logger.info("  Режим: ProxyAPI")
            logger.info(f"  Base URL: {settings.proxy_api_base_url}")
            logger.info(
                f"  API ключ: {'*' * 10}...{settings.proxy_api_key[-4:] if settings.proxy_api_key else 'НЕ ЗАДАН'}"
            )
            self.client = OpenAI(
                api_key=settings.proxy_api_key,
                base_url=settings.proxy_api_base_url,
            )
        self.model = settings.openai_model
        self.vision_model = settings.openai_vision_model
        
        logger.info("OpenAI сервис инициализирован успешно ✓")
        logger.info("=" * 50)
    
    def _parse_json_response(self, content: str) -> dict:
        """Извлечь JSON из ответа модели"""
        logger.debug(f"Парсинг JSON ответа, длина: {len(content)} символов")
        
        # Пробуем найти JSON в markdown блоке
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
            logger.debug("JSON найден в markdown блоке")
        
        # Пробуем найти JSON объект
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
            logger.debug("JSON объект извлечён")
        
        try:
            result = json.loads(content)
            logger.debug(f"JSON успешно распарсен, ключей: {len(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Проблемный контент: {content[:200]}...")
            return {}
    
    @staticmethod
    def _responses_output_text(response) -> str:
        """Текст ответа из Responses API (SDK output_text или разбор output)."""
        text = getattr(response, "output_text", None)
        if text:
            return text
        parts: list[str] = []
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", None) or []:
                    if getattr(c, "type", None) == "output_text":
                        parts.append(getattr(c, "text", "") or "")
            elif getattr(item, "type", None) == "output_text":
                parts.append(getattr(item, "text", "") or "")
        return "".join(parts)
    
    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """Анализ текста конкурента"""
        logger.info("=" * 50)
        logger.info("📝 АНАЛИЗ ТЕКСТА КОНКУРЕНТА")
        logger.info(f"  Длина текста: {len(text)} символов")
        logger.info(f"  Превью: {text[:100]}...")
        logger.info(f"  Модель: {self.model}")
        
        system_prompt = """Ты — эксперт по конкурентному анализу. Проанализируй предоставленный текст конкурента и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
    "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", ...],
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "summary": "Краткое резюме анализа"
}

Важно:
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Будь конкретен и практичен в рекомендациях"""

        start_time = time.time()
        logger.info("  Отправка запроса к API...")
        
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=f"Проанализируй текст конкурента:\n\n{text}",
                temperature=0.7,
                max_output_tokens=2000,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = self._responses_output_text(response)
            logger.info(f"  Длина ответа: {len(content)} символов")
            usage = getattr(response, "usage", None)
            total = getattr(usage, "total_tokens", None) if usage else None
            logger.debug(f"  Использовано токенов: {total if total is not None else 'N/A'}")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", "")
            )
            
            logger.info(f"  Результат: {len(result.strengths)} сильных, {len(result.weaknesses)} слабых сторон")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_image(self, image_base64: str, mime_type: str = "image/jpeg") -> ImageAnalysis:
        """Анализ изображения (баннер, сайт, упаковка)"""
        logger.info("=" * 50)
        logger.info("🖼️ АНАЛИЗ ИЗОБРАЖЕНИЯ")
        logger.info(f"  Размер base64: {len(image_base64)} символов")
        logger.info(f"  MIME тип: {mime_type}")
        logger.info(f"  Модель: {self.vision_model}")
        
        system_prompt = """Ты — эксперт по визуальному маркетингу и дизайну. Проанализируй изображение конкурента (баннер, сайт, упаковка товара и т.д.) и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "description": "Детальное описание того, что изображено",
    "marketing_insights": ["инсайт 1", "инсайт 2", ...],
    "visual_style_score": 7,
    "visual_style_analysis": "Анализ визуального стиля конкурента",
    "recommendations": ["рекомендация 1", "рекомендация 2", ...]
}

Важно:
- visual_style_score от 0 до 10
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Оценивай: цветовую палитру, типографику, композицию, UX/UI элементы"""

        start_time = time.time()
        logger.info("  Отправка запроса к Vision API...")
        
        try:
            response = self.client.responses.create(
                model=self.vision_model,
                instructions=system_prompt,
                input=[
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Проанализируй это изображение конкурента с точки зрения маркетинга и дизайна:",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_base64}",
                                "detail": "auto",
                            },
                        ],
                    }
                ],
                temperature=0.7,
                max_output_tokens=2000,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = self._responses_output_text(response)
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            result = ImageAnalysis(
                description=data.get("description", ""),
                marketing_insights=data.get("marketing_insights", []),
                visual_style_score=data.get("visual_style_score", 5),
                visual_style_analysis=data.get("visual_style_analysis", ""),
                recommendations=data.get("recommendations", [])
            )
            
            logger.info(f"  Результат: оценка стиля {result.visual_style_score}/10")
            logger.info(f"  Инсайтов: {len(result.marketing_insights)}, рекомендаций: {len(result.recommendations)}")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_parsed_content(
        self, 
        title: Optional[str], 
        h1: Optional[str], 
        paragraph: Optional[str]
    ) -> CompetitorAnalysis:
        """Анализ распарсенного контента сайта"""
        logger.info("📄 Анализ распарсенного контента")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Абзац: {paragraph[:50] if paragraph else 'N/A'}...")
        
        content_parts = []
        if title:
            content_parts.append(f"Заголовок страницы (title): {title}")
        if h1:
            content_parts.append(f"Главный заголовок (H1): {h1}")
        if paragraph:
            content_parts.append(f"Первый абзац: {paragraph}")
        
        combined_text = "\n\n".join(content_parts)
        
        if not combined_text.strip():
            logger.warning("  ⚠ Контент пустой, возвращаем пустой анализ")
            return CompetitorAnalysis(
                summary="Не удалось извлечь контент для анализа"
            )
        
        return await self.analyze_text(combined_text)
    
    async def analyze_website_screenshot(
        self,
        screenshot_base64: str,
        url: str,
        title: Optional[str] = None,
        h1: Optional[str] = None,
        first_paragraph: Optional[str] = None
    ) -> CompetitorAnalysis:
        """Комплексный анализ сайта конкурента по скриншоту"""
        logger.info("=" * 50)
        logger.info("🌐 КОМПЛЕКСНЫЙ АНАЛИЗ САЙТА")
        logger.info(f"  URL: {url}")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Размер скриншота: {len(screenshot_base64)} символов base64")
        logger.info(f"  Модель: {self.vision_model}")
        
        # Формируем контекст из извлечённых данных
        context_parts = [f"URL сайта: {url}"]
        if title:
            context_parts.append(f"Title страницы: {title}")
        if h1:
            context_parts.append(f"Главный заголовок (H1): {h1}")
        if first_paragraph:
            context_parts.append(f"Текст на странице: {first_paragraph[:300]}")
        
        context = "\n".join(context_parts)
        logger.debug(f"  Контекст:\n{context}")
        
        system_prompt = """Ты — эксперт по конкурентному анализу и UX/UI дизайну. Проанализируй скриншот сайта конкурента и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
    "unique_offers": ["уникальное предложение/фича 1", "уникальное предложение/фича 2", ...],
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "summary": "Комплексное резюме анализа сайта конкурента",
    "ai_compliance_score": 7,
    "ai_training_recommendations": ["краткая рекомендация по структуре/разметке текста", "краткая рекомендация по ясности и полноте контента для датасета", ...]
}

Поле ai_compliance_score — целое число от 0 до 10: насколько видимый на скриншоте контент пригоден для использования в обучении LLM (структура, ясность, отсутствие мусора, читаемость, плотность смысла, отсутствие дублирования баннеров вместо текста и т.п.).

Поле ai_training_recommendations — 3-6 коротких пунктов: что улучшить на сайте, чтобы текст и подача лучше подходили для последующего обучения или дообучения языковых моделей (не общий маркетинг, а именно пригодность контента как учебного материала).

При анализе обращай внимание на:
- Дизайн и визуальный стиль (цвета, шрифты, композиция)
- UX/UI: навигация, расположение элементов, CTA кнопки
- Контент: заголовки, тексты, призывы к действию
- Уникальные торговые предложения (УТП)
- Целевая аудитория (на кого ориентирован сайт)
- Технологичность и современность дизайна

Важно:
- Каждый массив (кроме ai_training_recommendations по смыслу — там 3-6 пунктов) должен содержать 4-6 конкретных пунктов для strengths/weaknesses/unique_offers/recommendations
- Пиши на русском языке
- Будь конкретен и практичен
- Давай actionable рекомендации"""

        start_time = time.time()
        logger.info("  Отправка скриншота в Vision API...")
        
        try:
            response = self.client.responses.create(
                model=self.vision_model,
                instructions=system_prompt,
                input=[
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"Проведи комплексный конкурентный анализ этого сайта:\n\n{context}",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{screenshot_base64}",
                                "detail": "auto",
                            },
                        ],
                    }
                ],
                temperature=0.7,
                max_output_tokens=3000,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = self._responses_output_text(response)
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            raw_score = data.get("ai_compliance_score")
            ai_score: Optional[int] = None
            if raw_score is not None:
                try:
                    ai_score = max(0, min(10, int(raw_score)))
                except (TypeError, ValueError):
                    ai_score = None
            raw_train = data.get("ai_training_recommendations") or []
            if isinstance(raw_train, list):
                ai_train = [str(x).strip() for x in raw_train if str(x).strip()]
            else:
                ai_train = []
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", ""),
                ai_compliance_score=ai_score,
                ai_training_recommendations=ai_train,
            )
            
            logger.info(f"  Результат:")
            logger.info(f"    - AI compliance (LLM training): {ai_score if ai_score is not None else 'N/A'}/10")
            logger.info(f"    - Сильных сторон: {len(result.strengths)}")
            logger.info(f"    - Слабых сторон: {len(result.weaknesses)}")
            logger.info(f"    - УТП: {len(result.unique_offers)}")
            logger.info(f"    - Рекомендаций: {len(result.recommendations)}")
            logger.info(f"  Резюме: {result.summary[:100]}...")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise


# Глобальный экземпляр
logger.info("Создание глобального экземпляра OpenAI сервиса...")
openai_service = OpenAIService()
