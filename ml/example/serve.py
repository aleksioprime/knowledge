"""API для оценки стоимости квартиры моделью из model.joblib."""
from contextlib import asynccontextmanager
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

MODEL_PATH = 'model.joblib'


class Apartment(BaseModel):
    district: Literal['центр', 'север', 'юг', 'окраина']
    area: float = Field(gt=10, lt=500, description='Площадь, м²')
    rooms: int = Field(ge=1, le=10)
    floor: int = Field(ge=1)
    floors_total: int = Field(ge=1)
    year: int | None = Field(default=None, ge=1800, le=2030)


class Estimate(BaseModel):
    price: int
    price_per_m2: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Модель загружается один раз при старте, а не на каждый запрос
    app.state.model = joblib.load(MODEL_PATH)
    yield


app = FastAPI(title='Оценка квартиры', lifespan=lifespan)


@app.post('/predict')
def predict(request: Request, apartment: Apartment) -> Estimate:
    features = pd.DataFrame([apartment.model_dump()])
    price = float(request.app.state.model.predict(features)[0])
    return Estimate(price=round(price, -3), price_per_m2=round(price / apartment.area, -3))
