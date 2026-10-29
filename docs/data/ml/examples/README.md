# Оценка стоимости квартиры

Учебный пример ко всем заметкам раздела [Machine Learning](../README.md): данные → модель → API.

```bash
pip install -r requirements.txt

python generate_data.py   # пересоздать apartments.csv (уже лежит в папке)
python train.py           # обучить модель и сохранить model.joblib
uvicorn serve:app --reload
```

```bash
curl -X POST localhost:8000/predict -H 'Content-Type: application/json' \
  -d '{"district": "центр", "area": 60, "rooms": 2, "floor": 5, "floors_total": 9, "year": 2015}'
# {"price":21652000,"price_per_m2":361000}
```

Данные в `apartments.csv` выдуманы: цена зависит от района, площади, этажа и года постройки плюс случайный разброс около 8%.
