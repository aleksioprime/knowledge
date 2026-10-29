# Чтение изображения

Для чтения изображения необходимо импортировать библиотеки и прочитать файл в переменную:

```python
import cv2
import numpy as np

image = cv2.imread('pixel3x3.png')
print(image)
```

Пример результата:

```
[[[  0   0   0]
  [128 128 128]
  [255 255 255]]

 [[  0   0 255]
  [  0 255   0]
  [255   0   0]]

 [[255 255   0]
  [  0 255 255]
  [255   0 255]]]
```

Этот массив представляет собой изображение размером 3x3 пикселя, где каждый пиксель представлен в формате **BGR (Blue, Green, Red)**. Именно в таком формате читает изображения OpenCV. 

- **Первый уровень массива** представляет строки изображения.
- **Второй уровень массива** представляет столбцы изображения.
- **Третий уровень массива** представляет значения цветов (BGR) для каждого пикселя.

Размер массива можно узнать с помощью свойства `shape`

```python
print(image.shape)  # Вывод: (3, 3, 3)

# Множественное присваивание
height, width, channels = image.shape
```
## Отображение

На локальном компьютере:

```python
import cv2
import numpy as np

img = cv2.imread('RGB-image.png')
cv2.imshow('Image',img) #'Image' - заголовок окна, img - переменная, содержащая изображение

cv2.waitKey(0) #ожидает нажатия любой клавиши
cv2.destroyAllWindows() #закроет окно перед завершением скрипта
```

На Colab:

```python
import cv2
import numpy as np
from google.colab.patches import cv2_imshow


image = cv2.imread(path+'RGB-image.png')
cv2_imshow(image)
```

На Colab и Jupyter Notebook:

```python
import cv2
import numpy as np
from matplotlib import pyplot as plt
%matplotlib inline


image = cv2.imread(path+'RGB-image.png')
plt.imshow(image)
plt.show()

image2show = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
plt.imshow(image2show)
plt.show()
```
## Сохранение результатов

```python
​​​​​​​cv2.imwrite(filename, image)
```

- `filename`: строка, представляющая путь и имя файла, в который будет сохранено изображение. Расширение файла (например, `.jpg`, `.png`, `.bmp`) определяет формат сохраненного изображения.
- `image`: массив NumPy, представляющий изображение, которое необходимо сохранить.