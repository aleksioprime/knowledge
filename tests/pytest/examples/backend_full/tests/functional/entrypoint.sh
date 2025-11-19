#!/bin/sh

# Добавляем путь текущей директории в PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# Ждём, пока все сервисы станут доступными
python utils/waiters.py

# Запускаем pytest с заданными параметрами
pytest