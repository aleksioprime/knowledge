# Модель в FastAPI

Модель, которая живёт в ноутбуке, приносит пользу только её автору. Чтобы оценка квартиры появилась на сайте или в мобильном приложении, модель нужно отдать через API: сайт присылает параметры квартиры, сервис возвращает цену. Для этого хватает [FastAPI](../../backend/frameworks/fastapi/README.md) и пары десятков строк.

Код — [examples/serve.py](examples/serve.py). Сначала обучите модель: `python train.py` (см. [Первая модель](first_model.md)).

## Минимальный пример

```python
# serve.py
from contextlib import asynccontextmanager
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field


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
    app.state.model = joblib.load('model.joblib')
    yield


app = FastAPI(title='Оценка квартиры', lifespan=lifespan)


@app.post('/predict')
def predict(request: Request, apartment: Apartment) -> Estimate:
    features = pd.DataFrame([apartment.model_dump()])
    price = float(request.app.state.model.predict(features)[0])
    return Estimate(price=round(price, -3), price_per_m2=round(price / apartment.area, -3))
```

```bash
uvicorn serve:app

curl -X POST localhost:8000/predict -H 'Content-Type: application/json' \
  -d '{"district": "центр", "area": 60, "rooms": 2, "floor": 5, "floors_total": 9, "year": 2015}'
# {"price":21652000,"price_per_m2":361000}
```

## Как это работает

**Модель загружается один раз** — в `lifespan` при старте приложения. Загрузка с диска медленнее, чем само предсказание. Если загружать модель на каждый запрос, сервис будет отвечать в разы медленнее. С загруженной моделью сто запросов в тестах заняли 0,69 секунды.

**Схема Pydantic проверяет вход** ещё до модели. Модели всё равно, что ей передали: она честно «оценит» квартиру площадью 0 м² в районе «марс». API отсекает такое сразу:

```text
422 district: Input should be 'центр', 'север', 'юг' or 'окраина'
422 area: Input should be greater than 10
```

**Пропуски обрабатывает сама модель.** `year` необязательный: если его не прислали, `SimpleImputer` внутри Pipeline подставит медиану, как при обучении. Это ещё одна причина хранить подготовку данных и модель одним объектом.

**`def`, а не `async def`.** Предсказание — вычисление на процессоре, а не ожидание сети. Синхронную функцию FastAPI выполнит в отдельном потоке и не заблокирует остальные запросы (см. [def или async def](../../backend/frameworks/fastapi/first_app.md#def-или-async-def)).

## Что ещё нужно в продакшене

- **Версия модели в ответе и логах.** Когда модель переобучили, а цены «поехали», нужно понимать, какая модель дала ответ. Добавьте поле `model_version` в `Estimate`.
- **Мониторинг предсказаний.** Распределение входящих данных меняется со временем: появляются новые районы, растут цены. Метрики в [Prometheus](../../infrastructure/monitoring/prometheus/README.md) — среднее предсказание, доля запросов с пропущенным годом — помогают заметить, что модель устарела.
- **Модель вне образа.** Модель весит мегабайты или гигабайты и обновляется чаще кода. Её хранят в [S3](../../backend/databases/s3/README.md) или в реестре моделей (MLflow) и скачивают при старте.
- **Пакетные предсказания.** Если нужно оценить миллион квартир раз в сутки, API не нужен: это задача для фонового задания или пайплайна в [Airflow](../engineering/airflow/README.md).

## Частые ошибки

- **Разные версии scikit-learn при обучении и в сервисе.** Модель, сохранённая одной версией, в другой может не загрузиться или предсказывать иначе; scikit-learn предупреждает об этом `InconsistentVersionWarning`. Закрепляйте версии в `requirements.txt` и обучайте в том же окружении, где работает сервис.
- **Признаки в другом порядке или с другими именами.** Pipeline ожидает те же колонки, что при обучении. Передавайте `DataFrame` с теми же именами колонок, а не просто список чисел.
- **Модель отвечает на всё.** Без проверки входа она молча выдаёт ерунду для невозможных данных.
- **Загрузка модели в каждом запросе.** Сервис медленный, а память скачет.
- **`joblib.load` чужого файла.** Внутри joblib — pickle, и загрузка файла может выполнить произвольный код. Загружайте только модели из своего доверенного хранилища.

## Связанные темы

- [Первая модель](first_model.md)
- [Схемы запросов и ответов в FastAPI](../../backend/frameworks/fastapi/schemas.md)
- [Docker Compose](../../infrastructure/devtools/docker/compose.md) — как упаковать сервис
