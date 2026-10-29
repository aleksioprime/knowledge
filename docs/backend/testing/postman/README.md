# Postman и Newman

Вы поменяли эндпоинт и хотите быстро проверить, что API по-прежнему работает: зарегистрироваться, войти, создать задачу, отметить её выполненной. Делать это через `curl`, копируя токен руками, утомительно. Postman — приложение для ручной работы с HTTP API: запросы собираются в **коллекции**, токен и id подставляются из переменных, а к каждому запросу можно приложить проверки. Newman запускает ту же коллекцию из командной строки, поэтому её можно гонять и в CI.

Перед работой с инструментом полезно разобраться в [структуре HTTP-запросов и ответов](../../web/http/request_response.md).

## Минимальный пример

У «Задачника» есть готовая коллекция: [../../../practice/projects/tasker/postman/tasker.postman_collection.json](../../../practice/projects/tasker/postman/tasker.postman_collection.json). В Postman: Import → выбрать файл. Или сразу из терминала, без установки:

```bash
cd docs/practice/projects/tasker/postman
docker run --rm -v "$PWD":/etc/newman postman/newman:6-alpine \
  run tasker.postman_collection.json --env-var baseUrl=http://host.docker.internal:8000
```

```text
→ Регистрация
  POST http://host.docker.internal:8000/auth/register [201 Created, 179B, 179ms]
  ✓  Пользователь создан
→ Вход
  POST http://host.docker.internal:8000/auth/token [200 OK, 286B, 150ms]
  ✓  Токен выдан
...
→ Удалённой задачи нет
  GET http://host.docker.internal:8000/tasks/193 [404 Not Found, 177B, 11ms]
  ✓  404 и понятное сообщение

│              requests │                 9 │                 0 │
│            assertions │                10 │                 0 │
```

`host.docker.internal` — адрес вашей машины изнутри контейнера Docker Desktop. Если Newman установлен локально (`npm install -g newman`), подойдёт обычный `localhost`.

## Как это работает

**Коллекция** — набор запросов, выполняемых по порядку. В «Задачнике»: регистрация → вход → создание задачи → неверные данные → выполнение → статистика → запрос без токена → удаление → проверка, что задачи нет.

**Переменные** записываются как `{{имя}}` в адресе, заголовках и теле. Они бывают на уровне коллекции, окружения (local, staging) и глобальные. `baseUrl` — классический пример: та же коллекция работает с любым стендом.

**Скрипты** — JavaScript, который выполняется до запроса (pre-request) или после (tests). Через них передают данные между запросами:

```javascript
// pre-request запроса «Регистрация»: новый email при каждом запуске, чтобы регистрация не упала с 409
pm.collectionVariables.set('email', `user-${Date.now()}@example.com`);
```

```javascript
// tests запроса «Вход»: проверяем ответ и запоминаем токен
pm.test('Токен выдан', () => {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json().token_type).to.eql('bearer');
});
pm.collectionVariables.set('token', pm.response.json().access_token);
```

Следующие запросы используют токен через вкладку Authorization → Bearer Token → `{{token}}`, а id созданной задачи — через `{{taskId}}` в адресе: `{{baseUrl}}/tasks/{{taskId}}`.

## Проверки

Проверки пишутся на библиотеке Chai:

```javascript
pm.test('Ошибки в названии и приоритете', () => {
    pm.response.to.have.status(422);
    const fields = pm.response.json().detail.map(error => error.loc.at(-1));
    pm.expect(fields).to.have.members(['title', 'priority']);
});

pm.test('Ответ быстрее 500 мс', () => pm.expect(pm.response.responseTime).to.be.below(500));
```

Если хоть одна проверка не прошла, Newman завершится с ненулевым кодом. Поэтому шаг в CI упадёт, и проблему заметят.

## Newman в CI

```yaml
# фрагмент .github/workflows/...
- name: Проверить API коллекцией Postman
  run: |
    npx newman run docs/practice/projects/tasker/postman/tasker.postman_collection.json \
      --env-var baseUrl=http://localhost:8000 \
      --reporters cli,junit --reporter-junit-export newman-report.xml
```

Отчёт в формате JUnit понимают GitHub Actions, GitLab и Jenkins.

## Postman или pytest

Коллекция проверяет **работающий** сервис снаружи, как это делает клиент: удобно после деплоя на стенд, для ручного исследования API и для тестировщиков без Python. Тесты [pytest](../pytest/README.md) запускаются внутри проекта, подменяют зависимости и проверяют граничные случаи гораздо подробнее. Обычно нужны оба: pytest — основная защита, коллекция — быстрая проверка стенда.

## Частые ошибки

- **Захардкоженные адреса и токены.** `http://localhost:8000` и вставленный руками токен в каждом запросе. Выносите их в переменные.
- **Коллекция зависит от данных стенда.** Запрос «получить задачу 1» упадёт на чистой базе. Создавайте нужные данные в самой коллекции и сохраняйте их id в переменные.
- **Секреты в экспортированной коллекции.** При экспорте сохраняются и значения переменных. Пароли и ключи держите в окружении, которое не попадает в репозиторий, или передавайте через `--env-var`.
- **Лимиты API.** «Задачник» пускает не больше 5 попыток входа в минуту. Коллекция, которую запускают много раз подряд, получит 429.

## Связанные темы

- [Pytest](../pytest/README.md)
- [GitHub Actions](../../../infrastructure/cicd/github/README.md)
- [Учебный проект «Задачник»](../../../practice/projects/tasker/README.md)
