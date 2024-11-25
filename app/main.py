import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.cors import CORSMiddleware

# Инициализация базы данных
DATABASE_URL = "sqlite:///./facilities.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Модель таблицы в базе данных
class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    cohort_range = Column(String, nullable=False)  # Строка диапазона, например: "10-30"

# Функция получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Создаем FastAPI приложение
app = FastAPI(
    title="Спортивный рекомендационный сервис",
    description="Сервис определяет когортный уровень пользователя и рекомендует спортивные площадки.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["*"],
                   allow_headers=["*"])

# Определяем входные данные
class UserInput(BaseModel):
    fitness_level: int = Field(..., description="Уровень физической подготовки: 1 (начинающий), 2 (средний), 3 (продвинутый)", example=2)
    age_category: int = Field(..., description="Возрастная категория: 1 (детская), 2 (юношеская), 3 (взрослая), 4 (пожилая)", example=3)
    training_type: int = Field(..., description="Тип тренировок: 1 (силовые), 2 (кардио), 3 (групповые), 4 (индивидуальные)", example=1)
    training_goal: int = Field(..., description="Цель тренировок: 1 (здоровье), 2 (снижение веса), 3 (выносливость), 4 (достижения)", example=2)
    sports_facility: str = Field(..., description="Тип спортивной площадки: фитнес-центр, открытый стадион, тренажерный зал", example="фитнес-центр")
    group_or_individual: int = Field(..., description="Формат занятий: 1 (групповые), 2 (индивидуальные)", example=1)
    health_status: int = Field(..., description="Состояние здоровья: 1 (без ограничений), 2 (хронические заболевания), 3 (коррекция нагрузок)", example=1)
    training_frequency: int = Field(..., description="Количество тренировок в неделю", example=3)
    training_time: int = Field(..., description="Время тренировок: 1 (утро), 2 (день), 3 (вечер)", example=1)
    chronic_diseases: Optional[List[str]] = Field(None, description="Список хронических заболеваний", example=[])
    weight: float = Field(..., description="Вес пользователя (в кг)", example=70.0)
    height: float = Field(..., description="Рост пользователя (в см)", example=170.0)
    health_group: Optional[int] = Field(None, description="Группа здоровья по МКБ", example=None)
    skill_focus: Optional[List[int]] = Field(None, description="Навыки для улучшения: 1 (гибкость), 2 (координация)", example=[1])
    cooperation: bool = Field(..., description="Готовность к сотрудничеству с тренером и другими участниками", example=True)
    budget: Optional[float] = Field(None, description="Бюджет на тренировки", example=5000)

class Recommendation(BaseModel):
    cohort: int = Field(..., description="Числовое значение когорты", example=33)
    recommended_facilities: List[str] = Field(..., description="Рекомендуемые спортивные площадки", example=["Фитнес-центр", "Открытый стадион"])

class URLRequest(BaseModel):
    url: str

# Логика определения когорты
def determine_cohort(user: UserInput) -> int:
    cohort = 0
    cohort += user.fitness_level * 10
    cohort += user.age_category
    if user.training_goal == 4 and user.fitness_level == 3:
        cohort += 20
    if user.health_status == 3:
        cohort -= 10

    if user.training_frequency >= 4:
        cohort += 5
    if user.training_type in [1, 2] and user.health_status == 1:
        cohort += 5

    return cohort

# Основной маршрут API
@app.post("/recommendations", response_model=Recommendation)
async def get_recommendations(user: UserInput, db: Session = Depends(get_db)):
    try:
        cohort = determine_cohort(user)
        facilities = db.query(Facility).all()
        recommended_facilities = [
            facility.name for facility in facilities
            if cohort in range(*map(int, facility.cohort_range.split('-')))
        ]
        return Recommendation(cohort=cohort, recommended_facilities=recommended_facilities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки данных: {str(e)}")


@app.post("/api/preview")
async def get_url_preview(request: URLRequest):
    try:
        # Проверка, что URL начинается с http или https
        if not request.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Получаем HTML-страницу
        async with httpx.AsyncClient() as client:
            response = await client.get(request.url, timeout=10)
        response.raise_for_status()  # Вызывает ошибку, если статус не 200

        # Парсим страницу с помощью BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Извлечение Open Graph данных
        metadata = {
            "title": None,
            "description": None,
            "image": None
        }
        og_title = soup.find("meta", property="og:title")
        og_description = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        metadata["title"] = og_title["content"] if og_title else soup.title.string if soup.title else "Без названия"
        metadata["description"] = og_description["content"] if og_description else "Описание отсутствует"
        metadata["image"] = og_image["content"] if og_image else None

        return metadata

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"HTTP Request Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {e}")