# JavaScript в браузере

DOM, события, `fetch`, `localStorage` и другие Web API предоставляет браузер — они не являются частью самого языка JavaScript.

## DOM

```js
const button = document.querySelector('[data-save]')
const status = document.querySelector('[data-status]')

button.textContent = 'Сохранить'
button.classList.add('button--primary')
button.dataset.state = 'ready'
```

Для обычного текста используйте `textContent`. Вставка непроверенных данных через `innerHTML` создаёт риск XSS.

## События

```js
button.addEventListener('click', (event) => {
  event.preventDefault()
  status.textContent = 'Сохранено'
})
```

События проходят фазы capture и bubble. Делегирование позволяет одному обработчику обслуживать динамические дочерние элементы:

```js
document.querySelector('.user-list').addEventListener('click', (event) => {
  const button = event.target.closest('[data-user-id]')
  if (!button) return

  openUser(button.dataset.userId)
})
```

## HTTP-запросы

Подробно Fetch, Axios, HTTP-методы, JSON, отмена и обработка ошибок разобраны в разделе [HTTP-запросы в JavaScript](http_requests.md).

```js
async function createUser(data) {
  const response = await fetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}
```

Cookies текущего origin отправляются согласно их атрибутам. Для междоменных credentials нужны согласованные настройки `credentials` и CORS на сервере. Подробнее: [HTTP](../../web/http/README.md) и [браузерные атаки](../../web/security/browser_attacks.md).

## Хранилища

- `localStorage` сохраняет строки между сессиями и работает синхронно;
- `sessionStorage` ограничен вкладкой и её сессией;
- IndexedDB подходит для больших и структурированных данных;
- cookies автоматически участвуют в HTTP-запросах согласно своим атрибутам.

Не храните чувствительные токены в `localStorage`, если модель угроз допускает XSS: любой выполненный на странице скрипт сможет их прочитать.

## Очистка ресурсов

Удаляйте ненужные обработчики событий, интервалы, observers и незавершённые запросы. Особенно это важно для долгоживущих SPA-компонентов.
