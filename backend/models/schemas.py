"""
Pydantic схемы для API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# === Запросы ===

class TextAnalysisRequest(BaseModel):
    """Запрос на анализ текста"""
    text: str = Field(..., min_length=10, description="Текст для анализа")


class ParseDemoRequest(BaseModel):
    """Запрос на парсинг URL"""
    url: str = Field(..., description="URL для парсинга")


# === Ответы ===

class CompetitorAnalysis(BaseModel):
    """Структурированный анализ конкурента"""
    strengths: List[str] = Field(default_factory=list, description="Сильные стороны")
    weaknesses: List[str] = Field(default_factory=list, description="Слабые стороны")
    unique_offers: List[str] = Field(default_factory=list, description="Уникальные предложения")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    summary: str = Field("", description="Общее резюме")
    ai_compliance_score: Optional[int] = Field(
        None,
        ge=0,
        le=10,
        description="Готовность контента к использованию для обучения LLM (0–10); только для анализа по скриншоту сайта",
    )
    ai_training_recommendations: List[str] = Field(
        default_factory=list,
        description="Краткие рекомендации по оптимизации контента под обучение LLM",
    )


class ImageAnalysis(BaseModel):
    """Анализ изображения"""
    description: str = Field("", description="Описание изображения")
    marketing_insights: List[str] = Field(default_factory=list, description="Маркетинговые инсайты")
    visual_style_score: int = Field(0, ge=0, le=10, description="Оценка визуального стиля (0-10)")
    visual_style_analysis: str = Field("", description="Анализ визуального стиля")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")


class ParsedContent(BaseModel):
    """Результат парсинга страницы"""
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    first_paragraph: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ParseHistorySnapshot(BaseModel):
    """
    Снимок анализа конкурента для хранения в истории (parse).
    Отделён от CompetitorAnalysis: изменения в API/LLM-схеме не тянут историю автоматически —
    обновляйте только from_competitor_analysis и при необходимости миграции JSON.
    """
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    unique_offers: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""
    ai_compliance_score: Optional[int] = Field(
        None,
        ge=0,
        le=10,
    )
    ai_training_recommendations: List[str] = Field(default_factory=list)

    @classmethod
    def from_competitor_analysis(cls, c: CompetitorAnalysis) -> "ParseHistorySnapshot":
        return cls(
            strengths=list(c.strengths),
            weaknesses=list(c.weaknesses),
            unique_offers=list(c.unique_offers),
            recommendations=list(c.recommendations),
            summary=c.summary,
            ai_compliance_score=c.ai_compliance_score,
            ai_training_recommendations=list(c.ai_training_recommendations),
        )


class TextAnalysisResponse(BaseModel):
    """Ответ на анализ текста"""
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    """Ответ на анализ изображения"""
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class ParseDemoResponse(BaseModel):
    """Ответ на парсинг"""
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


# === История ===

class HistoryItem(BaseModel):
    """Элемент истории"""
    id: str
    timestamp: datetime
    request_type: str  # "text", "image", "parse"
    request_summary: str
    response_summary: str
    parse_analysis: Optional[ParseHistorySnapshot] = Field(
        default=None,
        description="Снимок анализа parse (ParseHistorySnapshot), не DTO ответа LLM",
    )


class HistoryResponse(BaseModel):
    """Ответ со списком истории"""
    items: List[HistoryItem]
    total: int

