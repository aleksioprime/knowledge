# Работа с видеопотоком

Видео для OpenCV — это последовательность кадров, каждый из которых — обычное изображение. Поэтому любая обработка картинки переносится на поток с камеры или файл: нужно открыть источник, читать кадры в цикле и вовремя остановиться. Источником может быть веб-камера, IP-камера или видеофайл — код одинаковый, меняется только аргумент `VideoCapture`.

## Минимальный пример

Чтение кадров с веб-камеры и показ их в окне до нажатия Esc. Та же программа читает файл, если вместо `0` передать путь.

```python
import cv2

cap = cv2.VideoCapture(0)          # 0 — первая веб-камера; 'video.mp4' — файл
if not cap.isOpened():
    raise RuntimeError('камера или файл недоступны')

while True:
    read_ok, frame = cap.read()    # frame — массив (h, w, 3), как от imread
    if not read_ok:
        break                      # файл закончился или камера отключилась

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # обработка кадра
    cv2.imshow('Video Stream', gray)

    if cv2.waitKey(20) == 27:      # Esc
        break

cap.release()
cv2.destroyAllWindows()
```

## Как это работает

### Источники видеопотока

1. **Камеры (веб-камеры и IP-камеры).** Веб-камеры подключаются к компьютеру напрямую и доступны по индексу. IP-камеры подключаются к сети и отдают поток по адресу, например `rtsp://192.168.1.10:554/stream`.
2. **Видеофайлы.** Обработку можно выполнять на записях, хранящихся на диске или доступных по сети.

### Основные функции OpenCV для видео

**Открытие источника.** `cap = cv2.VideoCapture(source)` создаёт объект захвата. Если `source` — число, это индекс камеры: `0` — первая подключённая камера, `1`, `2` — следующие. Если строка — путь к файлу или адрес потока.

Если камера не открылась (не подключена, занята другим приложением, нет прав), `cap.isOpened()` вернёт `False`. Исключения при этом не будет.

**Чтение кадров.** `read_ok, frame = cap.read()` возвращает два значения: флаг успеха и сам кадр. Для файла `read_ok` станет `False` на последнем кадре — так обычно и выходят из цикла.

**Отображение.** `cv2.imshow()` показывает кадр в окне. `cv2.waitKey(20)` ждёт нажатия клавиши в течение 20 миллисекунд и возвращает её код или `-1`, если ничего не нажато. Код `27` — это Esc. Задержка нужна не только для клавиш: без `waitKey` окно не успевает перерисоваться.

**Освобождение ресурсов.** `cap.release()` отключает камеру или закрывает файл, `cv2.destroyAllWindows()` закрывает окна.

**Свойства потока.** Через `cap.get` можно узнать размер кадра, частоту и число кадров в файле:

```python
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))   # 0 для камеры
print(width, height, fps, total)                 # 1280 720 30.0 450
```

### Обработка видеопотока с камеры

```python
import cv2

cap = cv2.VideoCapture(0)

while cap.isOpened():
    read_ok, frame = cap.read()
    if not read_ok:
        break

    cv2.imshow('Video Stream', frame)

    if cv2.waitKey(20) == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

### Обработка видеопотока из файла

```python
import cv2

cap = cv2.VideoCapture('example_video.mp4')

while cap.isOpened():
    read_ok, frame = cap.read()
    if not read_ok:
        break

    cv2.imshow('Video File', frame)

    if cv2.waitKey(20) == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

### Запись результата в файл

`cv2.VideoWriter` принимает имя файла, кодек, частоту кадров и размер кадра `(ширина, высота)`. Размер обязан совпадать с кадрами, иначе файл получится пустым.

```python
import cv2

cap = cv2.VideoCapture('example_video.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

writer = cv2.VideoWriter('result.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, size)

while True:
    read_ok, frame = cap.read()
    if not read_ok:
        break
    writer.write(frame)

cap.release()
writer.release()
```

### Обработка видео в Colab

В Colab нет окон, поэтому кадры обрабатывают без `imshow`, а результат показывают анимацией matplotlib.

```python
import cv2
import imageio
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from IPython.display import HTML

def display_video(path):
    video = imageio.mimread(path)
    fig = plt.figure(figsize=(3, 3))

    frames = []
    for frame in video:
        img = plt.imshow(frame, animated=True)
        plt.axis('off')
        frames.append([img])

    anime = animation.ArtistAnimation(fig, frames, interval=50, repeat_delay=1000)
    plt.close()
    return HTML(anime.to_html5_video())

filename = 'example_video.mp4'
cap = cv2.VideoCapture(filename)

while cap.isOpened():
    read_ok, frame = cap.read()
    if not read_ok:
        break
    # здесь код обработки кадра

cap.release()
display_video(filename)
```

## Частые ошибки

- Нет проверки `isOpened()` → камера не открылась, `cap.read()` возвращает `(False, None)`, и код падает на `frame.shape` с `AttributeError` → проверять сразу после `VideoCapture`.
- Цикл без `waitKey` → окно не обновляется и «зависает», хотя кадры читаются → вызывать `cv2.waitKey(1)` на каждой итерации.
- `cv2.waitKey(20) == ord('q')` не срабатывает на некоторых системах → функция возвращает код с лишними битами → сравнивать `cv2.waitKey(20) & 0xFF == ord('q')`.
- `VideoWriter` с размером `(height, width)` или размером не того кадра → файл создаётся, но весит ноль байт → передавать `(width, height)` и убедиться, что обработанный кадр того же размера и трёхканальный.
- Файл не закрыт `release()` → при записи видео последние кадры теряются, а камера остаётся занятой для следующего запуска → всегда освобождать ресурсы, удобно через `try/finally`.
- Обработка каждого кадра тяжёлой моделью → кадры с камеры накапливаются в буфере, картинка отстаёт на секунды → обрабатывать каждый n-й кадр или читать кадры в отдельном потоке и брать последний.

## Когда не использовать

`VideoCapture` читает кадры последовательно и подходит для обработки «кадр за кадром». Если нужно перекодировать, обрезать по времени или склеить файлы без анализа содержимого, `ffmpeg` сделает это быстрее и без потери качества на лишнем декодировании.

Для десятков камер или потоков с высокой частотой один Python-цикл не справится: кадры декодируются в одном потоке. Там используют GStreamer, DeepStream или читают потоки в отдельных процессах. Для показа видео в веб-приложении кадры передают через MJPEG или WebRTC, а не через `imshow`.

## Связанные темы

- [Чтение изображения](read_image.md)
- [Работа с цветами](color_processing.md)
- [Поиск пикселя по цвету](find_pixel.md)
