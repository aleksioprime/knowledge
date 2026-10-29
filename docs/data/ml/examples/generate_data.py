"""Генерирует учебный набор данных о квартирах: apartments.csv.

Цена зависит от площади, района, этажа и года постройки, плюс случайный шум.
Данные выдуманы, зато воспроизводимы и не требуют скачивания.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 2000

districts = rng.choice(['центр', 'север', 'юг', 'окраина'], size=n, p=[0.2, 0.3, 0.3, 0.2])
area = rng.normal(55, 18, n).clip(18, 160).round(1)
rooms = np.clip(np.round(area / 22 + rng.normal(0, 0.5, n)), 1, 5).astype(int)
floors_total = rng.choice([5, 9, 12, 17, 25], size=n)
floor = np.array([rng.integers(1, total + 1) for total in floors_total])
year = rng.integers(1960, 2025, n)

price_per_m2 = pd.Series(districts).map({'центр': 320, 'север': 210, 'юг': 230, 'окраина': 160}).to_numpy()
price_per_m2 = price_per_m2 * (1 + (year - 1990) * 0.004)
price_per_m2 = price_per_m2 * np.where((floor == 1) | (floor == floors_total), 0.92, 1.0)
price = area * price_per_m2 * 1000 * rng.normal(1, 0.08, n)

df = pd.DataFrame({
    'district': districts,
    'area': area,
    'rooms': rooms,
    'floor': floor,
    'floors_total': floors_total,
    'year': year,
    'price': (price / 1000).round() * 1000,
})

# Немного «грязи», как в настоящих данных
df.loc[rng.choice(n, 30, replace=False), 'year'] = np.nan
df.loc[rng.choice(n, 5, replace=False), 'area'] = 0

df.to_csv('apartments.csv', index=False)
print(df.shape)
