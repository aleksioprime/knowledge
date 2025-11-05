**Строитель (Builder)** — это паттерн проектирования, который **разделяет процесс пошагового создания сложного объекта и его представление**.  
Главная идея: объект строится по шагам, и на каждом этапе можно управлять деталями его создания.

- **Пошаговое создание:** Объект создаётся не одним махом, а по частям (например, сначала строим стены, потом крышу и т.д.).
- **Один и тот же процесс построения** может создавать разные представления (например, деревянный дом или кирпичный дом).
- **Строитель может хранить состояние строящегося объекта**, а не возвращать сразу результат.
- **Отделение алгоритма создания** от конкретного результата.

```python
class Building:
    """Базовый класс-строитель, определяет шаги."""
    def build_floor(self):
        raise NotImplementedError

    def build_size(self):
        raise NotImplementedError

    def __repr__(self):
        return f"Floor: {self.floor} | Size: {self.size}"

# Конкретные строители
class House(Building):
    def build_floor(self):
        self.floor = 'One'

    def build_size(self):
        self.size = 'Big'

class Flat(Building):
    def build_floor(self):
        self.floor = 'More than one'

    def build_size(self):
        self.size = 'Small'

# Строитель для более сложных случаев
class ComplexBuilding:
    def __repr__(self):
        return f"Floor: {self.floor} | Size: {self.size}"

class ComplexHouse(ComplexBuilding):
    def build_floor(self):
        self.floor = 'One'

    def build_size(self):
        self.size = 'Big and fancy'

# Вынесем процесс создания в отдельную функцию (Director)
def construct_building(builder_cls):
    building = builder_cls()
    building.build_floor()
    building.build_size()
    return building

# Использование:
house = House()
house.build_floor()
house.build_size()
print(house)  # Floor: One | Size: Big

flat = Flat()
flat.build_floor()
flat.build_size()
print(flat)   # Floor: More than one | Size: Small

complex_house = construct_building(ComplexHouse)
print(complex_house)  # Floor: One | Size: Big and fancy
```

### Схема паттерна Builder на примере Бургера

1. **Builder (Строитель)** — интерфейс, определяющий шаги построения (определяет шаги по сборке бургера)
2. **ConcreteBuilder (Конкретный строитель)** — реализует шаги и хранит промежуточное состояние (реализует эти шаги для конкретного варианта)
3. **Director (Директор)** — управляет порядком вызова шагов (может быть опциональным) (управляет процессом сборки (задаёт порядок шагов))
4. **Product (Продукт)** — итоговый сложный объект (то, что строим (например, бургер))

```python
# Продукт
class Burger:
    def __init__(self):
        self.parts = []

    def add(self, part):
        self.parts.append(part)

    def __repr__(self):
        return "Burger with: " + ", ".join(self.parts)

# Абстрактный строитель (шаги)
class BurgerBuilder:
    def reset(self):
        self.burger = Burger()

    def add_bun(self):
        pass

    def add_patty(self):
        pass

    def add_lettuce(self):
        pass

    def add_sauce(self):
        pass

    def get_result(self):
        return self.burger

# Конкретный строитель — классический бургер
class ClassicBurgerBuilder(BurgerBuilder):
    def reset(self):
        super().reset()

    def add_bun(self):
        self.burger.add("bun")

    def add_patty(self):
        self.burger.add("beef patty")

    def add_lettuce(self):
        self.burger.add("lettuce")

    def add_sauce(self):
        self.burger.add("ketchup")

# Другой строитель — веганский бургер
class VeganBurgerBuilder(BurgerBuilder):
    def reset(self):
        super().reset()

    def add_bun(self):
        self.burger.add("vegan bun")

    def add_patty(self):
        self.burger.add("veggie patty")

    def add_lettuce(self):
        self.burger.add("lettuce")

    def add_sauce(self):
        self.burger.add("vegan mayo")

# Директор управляет процессом (какие шаги вызывать и в каком порядке)
class BurgerDirector:
    def __init__(self, builder):
        self.builder = builder

    def make_burger(self):
        self.builder.reset()
        self.builder.add_bun()
        self.builder.add_patty()
        self.builder.add_lettuce()
        self.builder.add_sauce()
        return self.builder.get_result()

# Использование
classic_builder = ClassicBurgerBuilder()
director = BurgerDirector(classic_builder)
burger = director.make_burger()
print(burger)  # Burger with: bun, beef patty, lettuce, ketchup

vegan_builder = VeganBurgerBuilder()
director = BurgerDirector(vegan_builder)
vegan_burger = director.make_burger()
print(vegan_burger)  # Burger with: vegan bun, veggie patty, lettuce, vegan mayo
```

Использование:

- Процесс сборки и детали реализации полностью отделены.
- Можно делать разные варианты продукта с одним и тем же процессом.
- Можно добавлять новые строители, не меняя остальной код.