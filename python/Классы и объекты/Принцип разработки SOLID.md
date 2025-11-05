**SOLID** - это принципы разработки программного обеспечения, следуя которым Вы получите хороший код, который в дальнейшем будет хорошо масштабироваться и поддерживаться в рабочем состоянии.

**S - Single Responsibility Principle - принцип единственной ответственности**. Каждый класс должен иметь только одну зону ответственности.

Плохо: Этот класс отвечает и за хранение текста, и за сохранение его в файл.

```python
class Report:
    def __init__(self, text):
        self.text = text

    def save_to_file(self, filename):
        with open(filename, 'w') as f:
            f.write(self.text)
```

Хорошо: Теперь каждый класс отвечает только за одну задачу: Report — за данные, ReportSaver — за сохранение.

```python
class Report:
    def __init__(self, text):
        self.text = text

class ReportSaver:
    @staticmethod
    def save_to_file(report, filename):
        with open(filename, 'w') as f:
            f.write(report.text)
```

**O - Open closed Principle - принцип открытости-закрытости.**   
Классы должны быть открыты для расширения, но закрыты для изменения.

Плохо: Чтобы добавить новую фигуру, придется менять код метода `area`.

```python
class AreaCalculator:
    def area(self, shape):
        if isinstance(shape, Circle):
            return 3.14 * shape.radius ** 2
        elif isinstance(shape, Square):
            return shape.side * shape.side
        # и так далее...
```

Хорошо: Добавлять новые фигуры можно без изменений существующего кода.

```python
class Shape:
    def area(self):
        raise NotImplementedError

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    def area(self):
        return 3.14 * self.radius ** 2

class Square(Shape):
    def __init__(self, side):
        self.side = side
    def area(self):
        return self.side * self.side

# Теперь AreaCalculator просто вызывает метод area
def total_area(shapes):
    return sum(shape.area() for shape in shapes)
```

**L - Liskov substitution Principle - принцип подстановки Барбары Лисков.**   
Должна быть возможность вместо базового (родительского) типа (класса) подставить любой его подтип (класс-наследник), при этом работа программы не должна измениться.

Плохо: Замена Bird на Ostrich приводит к ошибкам.

```python
class Bird:
    def fly(self):
        print("Flying")

class Ostrich(Bird):
    def fly(self):
        raise Exception("Ostrich can't fly!")
```

Хорошо: Теперь нельзя случайно использовать Ostrich там, где требуется летать

```python
class Bird:
    pass

class FlyingBird(Bird):
    def fly(self):
        print("Flying")

class Ostrich(Bird):
    pass

# Используем FlyingBird, где ожидается умение летать
```

**I -  Interface Segregation Principle - принцип разделения интерфейсов.**   
Данный принцип обозначает, что не нужно заставлять клиента (класс) реализовывать интерфейс, который не имеет к нему отношения.

Плохо: Printer вынужден реализовать лишние методы.

```python
class Machine:
    def print(self): pass
    def scan(self): pass
    def fax(self): pass

class Printer(Machine):
    def print(self): print("Printing")
    def scan(self): pass  # Не нужен
    def fax(self): pass   # Не нужен
```

Хорошо: Класс реализует только нужные интерфейсы

```python
class PrinterInterface:
    def print(self): pass

class ScannerInterface:
    def scan(self): pass

class SimplePrinter(PrinterInterface):
    def print(self):
        print("Printing")

class MultifunctionPrinter(PrinterInterface, ScannerInterface):
    def print(self):
        print("Printing")
    def scan(self):
        print("Scanning")
```

**D - Dependency Inversion Principle - принцип инверсии зависимостей.**   
Модули верхнего уровня не должны зависеть от модулей нижнего уровня. И те, и другие должны зависеть от абстракции. Абстракции не должны зависеть от деталей. Детали должны зависеть от абстракций.

Плохо: UserRepository зависит от конкретной реализации БД.

```python
class MySQLDatabase:
    def connect(self): pass

class UserRepository:
    def __init__(self):
        self.db = MySQLDatabase()  # жёсткая зависимость
```

Хорошо: Теперь можно подставить любую реализацию Database

```python
class Database:
    def connect(self): pass

class MySQLDatabase(Database):
    def connect(self): pass

class UserRepository:
    def __init__(self, db: Database):
        self.db = db
```