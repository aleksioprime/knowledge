match-case заменяет повторяющиеся операторы if-else компактной структурой сравнения с шаблоном (появился в Python 3.10).

```python
day = "Monday"
match day:
	case "Sunday"    : print("Take it easy")
	case "Monday"    : print("Go to work")
	case "Tuesday"   : print("Work + Hobbies")
	case "Wednesday" : print("Meetings")
	case "Thursday"  : print("Presentations")
	case "Friday"    : print("Interviews and party")
	case "Saturday"  : print("Time to do sports")
```

- **match element** означает «сопоставьте элемент со следующими шаблонами»
- затем каждое выражение **case pattern** сравнивает элемент с указанным шаблоном (это может быть, например, строка или число)
- если шаблон соответствует элементу, выполняется соответствующий блок кода, после этого оператор match-case заканчивает свою работу.

```python
point = (0, 10)

match point:
    case (0, y):
        print(f"На оси Y, y={y}")
    case (x, 0):
        print(f"На оси X, x={x}")
    case (x, y):
        print(f"В другой точке: x={x}, y={y}")
```

