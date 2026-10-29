# S3: хранение файлов

Пользователь прикрепляет к задаче отчёт или фотографию. Хранить файлы в PostgreSQL неудобно: база раздувается, резервные копии растут, а каждый запрос на скачивание проходит через приложение. Хранить на диске сервера тоже плохо: при второй копии сервиса файлы окажутся только на одной из машин. Обычное решение — **объектное хранилище** с API S3: файлы лежат отдельно, приложение хранит у себя только ключ файла, а скачивают его напрямую из хранилища по временной ссылке.

S3 — это сервис Amazon, но его API стал стандартом. Тот же код работает с Yandex Object Storage, VK Cloud, Selectel, Cloudflare R2 и локальными серверами вроде SeaweedFS.

```bash
pip install boto3
```

## Минимальный пример

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:8333',  # для AWS не указывается
    aws_access_key_id='tasker',
    aws_secret_access_key='tasker-secret',
    region_name='us-east-1',
    config=Config(signature_version='s3v4'),
)

s3.create_bucket(Bucket='tasker-attachments')
s3.upload_file(
    'report.txt', 'tasker-attachments', 'tasks/42/report.txt',
    ExtraArgs={'ContentType': 'text/plain; charset=utf-8'},
)

body = s3.get_object(Bucket='tasker-attachments', Key='tasks/42/report.txt')['Body'].read()
print(body.decode())  # Отчёт за октябрь
```

## Как это работает

- **Бакет** (bucket) — контейнер для файлов, примерно как диск. Имя бакета уникально в пределах хранилища.
- **Объект** — файл вместе с метаданными: типом содержимого, размером, датой изменения.
- **Ключ** — полное имя объекта, например `tasks/42/report.txt`. Настоящих папок нет: слэши — просто часть имени, но по ним удобно отбирать объекты префиксом.

```python
for obj in s3.list_objects_v2(Bucket='tasker-attachments', Prefix='tasks/42/')['Contents']:
    print(obj['Key'], obj['Size'])
# tasks/42/note.json 8
# tasks/42/report.txt 31

head = s3.head_object(Bucket='tasker-attachments', Key='tasks/42/report.txt')
head['ContentType'], head['ContentLength']  # ('text/plain; charset=utf-8', 31)

s3.delete_object(Bucket='tasker-attachments', Key='tasks/42/report.txt')
```

Файл нельзя дописать или изменить частично — только загрузить заново целиком.

## Временные ссылки (presigned URL)

Бакет закрыт: без ключей доступа скачать файл нельзя. Но и гнать каждый файл через своё приложение невыгодно. Поэтому приложение проверяет права пользователя и выдаёт **подписанную ссылку**, которая действует несколько минут:

```python
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'tasker-attachments', 'Key': 'tasks/42/report.txt'},
    ExpiresIn=600,  # 10 минут
)
# http://localhost:8333/tasker-attachments/tasks/42/report.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Signature=...
```

Ссылка содержит подпись, вычисленную секретным ключом. Хранилище проверяет её и срок действия:

```bash
curl "$URL"
# Отчёт за октябрь

curl localhost:8333/tasker-attachments/tasks/42/report.txt  # без подписи
# 403

curl "$EXPIRED_URL"
# <Error><Code>AccessDenied</Code><Message>Request has expired</Message>...
```

Изменить в ссылке имя файла тоже не выйдет: подпись перестанет совпадать, и хранилище ответит 403.

**Загрузка напрямую из браузера** устроена так же. Приложение выдаёт ссылку на `put_object`, и файл идёт из браузера сразу в хранилище, минуя сервер:

```python
upload_url = s3.generate_presigned_url(
    'put_object',
    Params={'Bucket': 'tasker-attachments', 'Key': 'tasks/42/photo.jpg', 'ContentType': 'image/jpeg'},
    ExpiresIn=600,
)
```

```bash
curl -X PUT -H 'Content-Type: image/jpeg' --data-binary @photo.jpg "$UPLOAD_URL"   # 200
curl -X PUT -H 'Content-Type: text/plain' --data-binary @photo.jpg "$UPLOAD_URL"   # 403
```

`ContentType` входит в подпись, поэтому по этой ссылке нельзя загрузить файл другого типа.

Типичный сценарий для вложений:

1. фронтенд просит у API ссылку на загрузку для задачи 42;
2. API проверяет, что задача принадлежит пользователю, придумывает ключ (`tasks/42/<uuid>.jpg`) и возвращает ссылку;
3. браузер загружает файл по ссылке;
4. API сохраняет ключ в базе. Для скачивания каждый раз выдаётся новая временная ссылка.

## Ошибки

```python
from botocore.exceptions import ClientError

try:
    s3.head_object(Bucket='tasker-attachments', Key='tasks/42/missing.txt')
except ClientError as error:
    error.response['Error']['Code']  # '404'

try:
    s3.get_object(Bucket='tasker-attachments', Key='tasks/42/missing.txt')
except s3.exceptions.NoSuchKey:
    ...  # The specified key does not exist.
```

Неверный секретный ключ даёт `SignatureDoesNotMatch`.

## S3 на своей машине

Для разработки нужен локальный сервер с API S3. Долгое время для этого почти всегда брали MinIO, но в октябре 2026 года официальные образы `minio/minio` больше не скачиваются ни с Docker Hub, ни с quay.io. Рабочие альтернативы — **SeaweedFS** и **LocalStack**. Ниже — SeaweedFS:

```yaml
# docker-compose.yaml
services:
  s3:
    image: chrislusf/seaweedfs:3.80
    command: server -s3 -s3.config=/etc/seaweedfs/s3.json -dir=/data
    ports:
      - "8333:8333"
    volumes:
      - ./s3.json:/etc/seaweedfs/s3.json
      - s3data:/data

volumes:
  s3data:
```

```json
{
  "identities": [
    {
      "name": "tasker",
      "credentials": [{"accessKey": "tasker", "secretKey": "tasker-secret"}],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
```

Без файла `s3.json` SeaweedFS вообще не проверяет подписи: подделанные и просроченные ссылки будут работать. Для экспериментов это удобно, но так легко не заметить ошибку, которая всплывёт на настоящем хранилище.

## Частые ошибки

- **Старый формат подписи.** С нестандартным `endpoint_url` boto3 может сгенерировать ссылку старого образца (`?AWSAccessKeyId=...&Signature=...`), которую AWS и многие другие хранилища уже не принимают. Указывайте `Config(signature_version='s3v4')`.
- **Публичный бакет «чтобы проще».** Все файлы всех пользователей становятся доступны любому, кто угадает ключ. Держите бакет закрытым и выдавайте временные ссылки.
- **Имя файла от пользователя как ключ.** Два файла `report.pdf` перезапишут друг друга, а имя может содержать что угодно. Генерируйте ключ сами (`tasks/42/<uuid>.pdf`), а исходное имя храните в базе.
- **Не указан `ContentType`.** Браузер может скачать картинку вместо того, чтобы её показать, или показать текст не в той кодировке.
- **Ссылка на часы или сутки.** Пересланная ссылка работает у любого, пока не истечёт. Для личных файлов хватает нескольких минут.

## Когда не использовать

Если файлов мало, они небольшие и сервис работает в одном экземпляре, объектное хранилище — лишний сервис и лишние ключи доступа: папка на диске и отдача через [NGINX](../../web/nginx/static_and_files.md) проще. Мелкие данные — аватар в пару килобайт, настройки, JSON — часто удобнее держать прямо в базе рядом с остальными полями: один запрос, одна транзакция, одна резервная копия.

S3 не подходит для файлов, которые часто дописывают или меняют частями (журналы, файлы SQLite): объект загружается только целиком. Для этого есть обычная файловая система или сетевой диск. И это не база: искать по содержимому и фильтровать по полям S3 не умеет, метаданные файлов хранят в PostgreSQL.

## Связанные темы

- [Передача файлов по HTTP](../../web/http/file_transfer.md)
- [Отдача статики через NGINX](../../web/nginx/static_and_files.md)
- [Учебный проект «Задачник»](../../../practice/projects/tasker/README.md)
