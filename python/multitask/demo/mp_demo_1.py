import time
import os

from multiprocessing import Process

# Функция, которая будет работать в отдельном процессе
def printer(name):
    time.sleep(20)
    print('привет', name)

if __name__ == '__main__':
    # Создаём объект процесса, передав в него функцию и аргументы, с которыми он будет вызван
    p = Process(target=printer, args=('Алиса',))
    # Запускаем
    p.start()
    print('Пока выполняется процесс, съешьте ещё этих мягких французских булок да выпейте чаю ☕️ ')
    # Выведем Process ID для текущего процесса и для процесса, который только что запустили
    print('Главный PID', os.getpid())
    print('Дочерний PID', p.pid)
    # Дождёмся выполнения процесса
    p.join()
    print('Завершение работы')