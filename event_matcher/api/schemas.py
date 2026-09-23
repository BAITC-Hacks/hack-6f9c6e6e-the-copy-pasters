from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OptionsResponse(BaseModel):
    cities: list[str]
    categories: list[str]
    event_formats: list[str]
    languages: list[str]


class MatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    city: str = Field(min_length=1, max_length=100)
    event_date: date
    event_format: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    budget_kzt: int = Field(gt=0, le=100_000_000)
    language: str | None = Field(default=None, max_length=100)
    hours: int | None = Field(default=None, ge=1, le=24)


class MatchResult(BaseModel):
    id: str
    name: str
    categories: list[str]
    city: str
    price_from_kzt: int
    event_formats: list[str]
    languages: list[str]
    max_hours: float | None
    busy_dates: list[str]
    synthetic: bool
    city_imputed: bool
    price_imputed: bool
    source: Literal["catalog", "personal"] = "catalog"
    explanation: str


class MatchResponse(BaseModel):
    status: Literal["matched", "no_category", "filtered_out"]
    candidate_count: int
    reasons: dict[str, int]
    matches: list[MatchResult] = Field(max_length=3)


class AuthCredentials(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class PersonalProviderInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    categories: list[str] = Field(min_length=1, max_length=10)
    city: str = Field(min_length=1, max_length=100)
    price_from_kzt: int = Field(ge=0, le=100_000_000)
    event_formats: list[str] = Field(min_length=1, max_length=10)
    languages: list[str] = Field(default_factory=list, max_length=10)
    max_hours: float | None = Field(default=None, ge=1, le=24)
    busy_dates: list[date] = Field(default_factory=list, max_length=100)
    description: str = Field(default="", max_length=4000)
    phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=300)
    social_link: str | None = Field(default=None, max_length=300)

    @field_validator("categories", "event_formats", "languages", mode="before")
    @classmethod
    def clean_list(cls, values):
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValueError("Передайте список значений")
        return [str(value).strip() for value in values if str(value).strip()]

    @field_validator("website", "social_link", mode="before")
    @classmethod
    def clean_links(cls, value):
        if value is None or not str(value).strip():
            return None
        value = str(value).strip()
        if not value.startswith(("https://", "http://")):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return value


class AIAnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    city: str | None = Field(default=None, max_length=100)
    event_date: date | None = None
    event_format: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    budget_kzt: int | None = Field(default=None, gt=0, le=100_000_000)
    language: str | None = Field(default=None, max_length=100)
    hours: int | None = Field(default=None, ge=1, le=24)
