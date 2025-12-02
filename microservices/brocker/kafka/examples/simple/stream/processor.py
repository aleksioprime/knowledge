"""
Пример простого потокового процессора с использованием Faust, который читает числа из топика "numbers",
удваивает их и отправляет в топик "numbers_processed"
"""
# pip install faust
# Запуск: faust -A processor worker -l info
import faust

# Создаём Faust-приложение, подключаемся к Kafka
app = faust.App(
    'demo-stream-app',
    broker='kafka://localhost:9096',
)

# Входной топик
input_topic = app.topic('numbers', value_type=int)

# Выходной топик
output_topic = app.topic('numbers_processed', value_type=int)

# Агенты Faust — это потоковые процессоры
@app.agent(input_topic)
async def process(numbers):
    async for number in numbers:
        result = number * 2
        print(f"[STREAM] {number} → {result}")
        await output_topic.send(value=result)