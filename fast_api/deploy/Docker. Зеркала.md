В связи с тем, что компания Docker заблокировала Docker Hub(hub.docker.com) для пользователей из России, необходимо добавить зеркала этого хоста в настройки Docker Desktop.

Для этого откройте страницу настроек `Settings` | `Docker Engine` и измените содержимое текстового поля следующим образом:

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://mirror.gcr.io",
    "https://dockerhub.timeweb.cloud/"
  ]
}
```

После этого нажмите кнопку `Apply & restart`.