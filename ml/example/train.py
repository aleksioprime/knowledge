"""Обучает модель цены квартиры и сохраняет её в model.joblib."""
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURES = ['district', 'area', 'rooms', 'floor', 'floors_total', 'year']

df = pd.read_csv('apartments.csv')
df = df[df['area'] > 0]

X, y = df[FEATURES], df['price']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

preprocess = ColumnTransformer([
    ('district', OneHotEncoder(handle_unknown='ignore'), ['district']),
    ('numbers', SimpleImputer(strategy='median'), ['area', 'rooms', 'floor', 'floors_total', 'year']),
])
model = make_pipeline(preprocess, HistGradientBoostingRegressor(random_state=42))
model.fit(X_train, y_train)

predictions = model.predict(X_test)
print(f'MAE:  {mean_absolute_error(y_test, predictions):,.0f} ₽'.replace(',', ' '))
print(f'MAPE: {mean_absolute_percentage_error(y_test, predictions):.1%}')

joblib.dump(model, 'model.joblib')
print('модель сохранена в model.joblib')
