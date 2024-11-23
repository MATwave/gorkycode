from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

# Создаем FastAPI приложение
app = FastAPI(title="Спортивный рекомендационный сервис")

# Определяем входные данные
class UserInput(BaseModel):
    fitness_level: int = Field(..., description="Уровень физической подготовки (1 - начинающий, 2 - средний, 3 - продвинутый)")
    age_category: int = Field(..., description="Возрастная категория (1 - детская, 2 - юношеская, 3 - взрослая, 4 - пожилая)")
    training_type: int = Field(..., description="Тип тренировок (1 - силовые, 2 - кардио, 3 - групповые, 4 - индивидуальные)")
    training_goal: int = Field(..., description="Цель тренировок (1 - здоровье, 2 - снижение веса, 3 - выносливость, 4 - достижения)")
    sports_facility: str = Field(..., description="Тип спортивной площадки (фитнес-центр, открытый стадион, тренажерный зал)")
    group_or_individual: int = Field(..., description="Формат занятий (1 - групповые, 2 - индивидуальные)")
    health_status: int = Field(..., description="Состояние здоровья (1 - без ограничений, 2 - хронические заболевания, 3 - коррекция нагрузок)")
    training_frequency: int = Field(..., description="Количество тренировок в неделю")
    training_time: int = Field(..., description="Время тренировок (1 - утро, 2 - день, 3 - вечер)")
    chronic_diseases: Optional[List[str]] = Field(None, description="Список хронических заболеваний")
    weight: float = Field(..., description="Вес пользователя (в кг)")
    height: float = Field(..., description="Рост пользователя (в см)")
    health_group: Optional[int] = Field(None, description="Группа здоровья по МКБ")
    skill_focus: Optional[List[int]] = Field(None, description="Навыки для улучшения (1 - гибкость, 2 - координация)")
    cooperation: bool = Field(..., description="Готовность к сотрудничеству с тренером и другими участниками")
    budget: Optional[float] = Field(None, description="Бюджет на тренировки")

# Определяем структуру ответа
class Recommendation(BaseModel):
    cohort: int
    recommended_facilities: List[str]

# Логика определения когорты
def determine_cohort(user: UserInput) -> int:
    # Начальные базовые правила
    cohort = 0
    cohort += user.fitness_level * 10  # Уровень физической подготовки
    cohort += user.age_category       # Возрастная категория

    # Уточняющие правила
    if user.training_goal == 4 and user.fitness_level == 3:
        cohort += 20  # Высокий уровень мотивации и подготовки
    if user.health_status == 3:
        cohort -= 10  # Коррекция нагрузок снижает общий "уровень"

    # Дополнительные параметры
    if user.training_frequency >= 4:
        cohort += 5  # Частые тренировки повышают уровень
    if user.training_type in [1, 2] and user.health_status == 1:
        cohort += 5  # Кардио или силовые тренировки без ограничений

    return cohort

# Логика фильтрации площадок
facility_to_cohorts = {
    "Фитнес-центр": range(20, 50),  # Подходит для когорт от 20 до 50
    "Открытый стадион": range(10, 40),  # Подходит для когорт от 10 до 40
    "Тренажерный зал": range(30, 60),  # Подходит для когорт от 30 до 60
    "Стадион для соревновательной подготовки": range(40, 70),  # Высокий уровень
}

def recommend_facilities(cohort: int) -> List[str]:
    facilities = [
        facility for facility, valid_cohorts in facility_to_cohorts.items()
        if cohort in valid_cohorts
    ]
    return facilities if facilities else ["Подходящих площадок не найдено"]

# Основной маршрут API
@app.post("/recommendations", response_model=Recommendation)
async def get_recommendations(user: UserInput):
    try:
        cohort = determine_cohort(user)
        facilities = recommend_facilities(cohort)
        return Recommendation(cohort=cohort, recommended_facilities=facilities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки данных: {str(e)}")