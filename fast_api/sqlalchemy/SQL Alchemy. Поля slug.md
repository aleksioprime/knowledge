Установка библиотеки Slugify:

```sh
pip install python-slugify
```

Функция `slugify` - конвертирует строку, преобразовывая пробелы в дефисы, удаляя символы которые не являются буквенно-цифровыми, подчеркиваниями или дефисами, конвертирует в нижний регистр и удаляет пробелы в начале и конце текста.

```python
category_model = Category(
	name=create_category.name,
	parent_id=create_category.parent_id,
	slug=slugify(create_category.name)
)
db.add(category_model)
db.commit()
```

