**SLAP** (Single Level of Abstraction Principle) — это принцип написания кода, согласно которому каждая функция/метод должна оперировать только на **одном уровне абстракции**.  
Идея: внутри одной функции не должно одновременно встречаться как работа “на верхнем уровне” (например, бизнес-логика), так и “низкоуровневые” детали (например, работа с файлами, циклы по элементам и т.п.).

- **Повышает читаемость**: код становится легче читать и поддерживать.
- **Облегчает тестирование**: маленькие функции проще тестировать.
- **Упрощает изменение кода**: изменение низкоуровневых деталей не требует менять бизнес-логику и наоборот.

Нарушение SLAP:

```python
def process_users(user_list):
    for user in user_list:
        if user.is_active:
            # Сохраняем логи
            with open("log.txt", "a") as f:
                f.write(f"{user.name} processed\n")
            # Отправляем email
            send_email(user.email, "Welcome back!")
```

Соблюдение SLAP:

```python
def process_users(user_list):
    for user in user_list:
        if user.is_active:
            log_user_processed(user)
            notify_user(user)

def log_user_processed(user):
    with open("log.txt", "a") as f:
        f.write(f"{user.name} processed\n")

def notify_user(user):
    send_email(user.email, "Welcome back!")
```