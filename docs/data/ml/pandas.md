# pandas: первое знакомство с данными

Прежде чем учить модель, нужно понять данные: сколько строк, какие колонки, где пропуски, нет ли явной ерунды вроде квартиры площадью 0 м². В Excel это неудобно уже на десятке тысяч строк, а писать циклы на чистом Python долго. pandas загружает таблицу в `DataFrame` и отвечает на такие вопросы одной строкой.

Пример — учебный набор из 2000 квартир: [examples/apartments.csv](examples/apartments.csv). Данные выдуманы скриптом [generate_data.py](examples/generate_data.py), зато воспроизводимы и не требуют скачивания.

```bash
pip install "pandas==3.0.*"
```

## Минимальный пример

```python
import pandas as pd

df = pd.read_csv('apartments.csv')
df.head(3)
```

```text
  district  area  rooms  floor  floors_total    year       price
0       юг  36.6      1      8             9  1974.0   8988000.0
1    север  71.3      3      1             5  2020.0  14715000.0
2  окраина  33.4      2     11            12  2011.0   5710000.0
```

```python
df['price_per_m2'] = df['price'] / df['area']
df.groupby('district')['price_per_m2'].median().round(-3).sort_values(ascending=False)
```

```text
district
центр      316000.0
юг         226000.0
север      207000.0
окраина    157000.0
```

Медианная цена квадратного метра по районам — одной строкой.

## Как это работает

- **`DataFrame`** — таблица: строки и именованные колонки, у каждой колонки свой тип;
- **`Series`** — одна колонка: `df['price']`.

Операции применяются **ко всей колонке сразу**, без циклов: `df['price'] / df['area']` делит каждую строку. Внутри это быстрые вычисления на массивах NumPy, поэтому миллионы строк обрабатываются за доли секунды.

## Осмотр данных

```python
df.shape  # (2000, 7)

df.info()
```

```text
 #   Column        Non-Null Count  Dtype
---  ------        --------------  -----
 0   district      2000 non-null   str
 1   area          2000 non-null   float64
 2   rooms         2000 non-null   int64
 5   year          1970 non-null   float64
 6   price         2000 non-null   float64
```

`year` заполнен только в 1970 строках из 2000 — значит, есть пропуски. Тип `float64` у года как раз из-за них: пропуск хранится как `NaN`, а это значение с плавающей точкой.

```python
df.describe().round(1)
```

```text
         area   rooms   year       price
count  2000.0  2000.0  1970.0      2000.0
mean     55.3     2.5  1991.9  12498817.0
min       0.0     1.0  1960.0   1873000.0
max     110.6     5.0  2024.0  41604000.0
```

`min` площади — 0. Квартир площадью ноль не бывает: это ошибка в данных.

```python
df.isna().sum()                   # пропуски по колонкам: year — 30
df['district'].value_counts()     # север 600, юг 579, окраина 413, центр 408
(df['area'] == 0).sum()           # 5
pd.crosstab(df['district'], df['rooms'])  # сколько квартир каждой комнатности в каждом районе
```

## Отбор строк и колонок

```python
df[df['district'] == 'центр']                               # условие
df[(df['district'] == 'центр') & (df['rooms'] >= 3)]        # 197 строк — несколько условий
df[['district', 'price']]                                   # нужные колонки
df.loc[df['price'].idxmax(), ['district', 'area', 'price']] # строка с максимальной ценой
df.sort_values('price', ascending=False).head(3)            # три самые дорогие
```

Условия объединяют через `&` (и), `|` (или), `~` (не), и каждое берут в скобки. Обычные `and` и `or` здесь не работают.

## Группировка

```python
df.groupby('district').agg(
    count=('price', 'size'),
    median_price=('price', 'median'),
    mean_area=('area', 'mean'),
).round(1)
```

```text
          count  median_price  mean_area
district
окраина     413     8789000.0       55.3
север       600    11456500.0       55.2
центр       408    17584000.0       55.4
юг          579    12496000.0       55.5
```

Это то же самое, что `GROUP BY` в [SQL](../../backend/databases/sql/basics.md).

## Очистка

```python
clean = df[df['area'] > 0].copy()                           # убрать явные ошибки
clean['year'] = clean['year'].fillna(clean['year'].median())  # заполнить пропуски медианой
clean.shape  # (1995, 8)
```

Что делать с пропусками — решение, а не формальность: удалить строки, заполнить медианой, заполнить отдельным значением «неизвестно». От выбора зависит, чему научится модель.

## pandas 3: что изменилось

В старых статьях встречаются вещи, которые в pandas 3 работают иначе:

- **копирование при записи** (copy-on-write) включено всегда. Изменение отфильтрованной части больше не меняет исходную таблицу, и знаменитое предупреждение `SettingWithCopyWarning` исчезло:

  ```python
  south = df[df['district'] == 'юг']
  south['price'] = 0
  (df['price'] == 0).any()  # False — исходная таблица не изменилась
  ```

  Чтобы изменить исходную таблицу, пишут через `df.loc[условие, 'колонка'] = значение`;

- **строковые колонки** получили свой тип `str` вместо универсального `object`. Они быстрее и занимают меньше памяти.

## Частые ошибки

- **`and` вместо `&`.** `df[df['rooms'] > 2 and df['area'] > 50]` упадёт с `ValueError: The truth value of a Series is ambiguous`.
- **Деление на ноль без проверки.** Цена квадратного метра для квартиры площадью 0 станет `inf`. Среднее по такой колонке будет бесконечным, медиана — нет. Чистите данные до расчётов.
- **Цикл по строкам.** `for i, row in df.iterrows()` в сотни раз медленнее операций над колонками. Почти всегда есть векторный способ.
- **Цепочка присваиваний.** `df[df['district'] == 'юг']['price'] = 0` в pandas 3 ничего не изменит, а pandas выведет предупреждение `ChainedAssignmentError: A value is being set on a copy of a DataFrame or Series through chained assignment`. Используйте `df.loc[df['district'] == 'юг', 'price'] = 0`.

## Связанные темы

- [Первая модель](first_model.md)
- [NumPy: массивы](../cv/numpy/array.md)
- [Основы SQL](../../backend/databases/sql/basics.md)
