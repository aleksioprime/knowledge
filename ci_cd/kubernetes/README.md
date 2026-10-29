# Kubernetes

Docker Compose хорошо управляет контейнерами на **одной** машине. Но если машина упала, упало всё. Если нагрузка выросла, нужно руками поднимать копии на других серверах. Если выкатили сломанную версию, откатываться тоже приходится вручную. Kubernetes управляет контейнерами на **кластере** машин. Вы описываете желаемое состояние («3 копии этого сервиса, доступные по такому адресу»), а Kubernetes постоянно приводит систему к нему: перезапускает упавшее, распределяет копии по машинам, обновляет версии без остановки.

Пример — в папке [example](example/): небольшой сервис на FastAPI и манифест [k8s.yaml](example/k8s.yaml).

## Свой кластер за минуту

Для экспериментов не нужен облачный кластер. Лёгкий дистрибутив k3s запускается обычным Docker-контейнером, а `kubectl` в нём уже есть:

```bash
docker run -d --privileged --name k3s -p 8088:80 rancher/k3s:v1.31.4-k3s1 server
alias k='docker exec -i k3s kubectl'
k get nodes
# NAME           STATUS   ROLES    AGE   VERSION
# d8f56c8870e5   Ready    <none>   1s    v1.31.4+k3s1
```

Образ, собранный у себя, нужно передать внутрь кластера: у k3s своё хранилище образов, отдельное от Docker.

```bash
cd example
docker build --build-arg VERSION=1.0 -t hello-app:1.0 app
docker save hello-app:1.0 | docker exec -i k3s ctr images import -
```

Другие варианты для локальной работы — minikube, kind и Kubernetes, встроенный в Docker Desktop. Чем они отличаются и как поднять кластер из нескольких узлов на kind — в заметке [«Кластер Kubernetes»](docs/cluster.md#локальные-кластеры).

## Минимальный пример

```bash
k apply -f - < k8s.yaml
k rollout status deployment/hello
# deployment "hello" successfully rolled out

k get pods
# hello-647c785d55-6kx2n   1/1   Running
# hello-647c785d55-cwnwj   1/1   Running
# hello-647c785d55-zswbh   1/1   Running

curl localhost:8088/
# {"pod":"hello-647c785d55-zswbh","version":"1.0","greeting":"Привет из Kubernetes","has_secret":true}
```

На 30 запросов каждый из трёх подов ответил по 10 раз: нагрузка распределяется поровну.

## Основные объекты

**Pod** — минимальная единица: один или несколько контейнеров с общей сетью. Поды смертны: при сбое, обновлении или переезде на другую машину под удаляется и создаётся новый, с другим именем и адресом. Поэтому поды почти никогда не создают руками.

**Deployment** описывает, какие поды нужны и сколько:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hello
  template:              # шаблон пода
    metadata:
      labels:
        app: hello
    spec:
      containers:
        - name: app
          image: hello-app:1.0
          ports:
            - containerPort: 8000
```

**Service** — постоянный адрес для набора подов. Он находит поды по меткам (`app: hello`) и распределяет между ними запросы. Внутри кластера сервис доступен по имени: `http://hello`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello
spec:
  selector:
    app: hello
  ports:
    - port: 80
      targetPort: 8000
```

**Ingress** — правила входа снаружи: какой домен и путь в какой сервис отправить. В k3s их выполняет встроенный [Traefik](../../microservices/api_gateway/README.md).

**ConfigMap** и **Secret** — настройки и секреты, которые подставляются в контейнер как переменные окружения или файлы:

```yaml
envFrom:
  - configMapRef:
      name: hello-config
  - secretRef:
      name: hello-secret
```

## Kubernetes сам чинит систему

Удалим под, будто машина упала:

```bash
k delete pod hello-647c785d55-6kx2n
k get pods
# hello-647c785d55-cwnwj   1/1   Running   17s
# hello-647c785d55-gzsvv   0/1   Running   1s    ← уже создан взамен
# hello-647c785d55-zswbh   1/1   Running   17s
```

Deployment хотел три пода, увидел два и тут же создал третий. Масштабирование работает так же:

```bash
k scale deployment/hello --replicas=5
```

## Проверки здоровья

```yaml
readinessProbe:      # готов ли под принимать запросы
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 5
livenessProbe:       # жив ли под; если нет — перезапустить контейнер
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 10
```

Пока `readinessProbe` не прошла, Service не отправляет поду запросы. Отсюда `0/1 Running` у только что созданного пода: процесс уже работает, но ещё не готов.

## Обновление без остановки

```bash
docker build --build-arg VERSION=2.0 -t hello-app:2.0 app
docker save hello-app:2.0 | docker exec -i k3s ctr images import -

k set image deployment/hello app=hello-app:2.0
k rollout status deployment/hello
curl localhost:8088/
# {"pod":"hello-6995d6b64f-vlkbq","version":"2.0",...}
```

Kubernetes заменяет поды по очереди: поднимает новый, ждёт его готовности, гасит старый.

**Подвох.** В первой версии примера во время обновления 3 из 60 запросов закончились ошибками 502 и 504. Старый под уже получил команду остановиться, а Ingress ещё несколько мгновений отправлял ему запросы. Решение — дать поду время, чтобы его успели убрать из балансировки:

```yaml
spec:
  terminationGracePeriodSeconds: 30
  containers:
    - name: app
      lifecycle:
        preStop:
          sleep:
            seconds: 5
```

После этого все 100 запросов во время обновления вернули 200. Действие `sleep` в `preStop` доступно с Kubernetes 1.30. В старых версиях пишут `exec: {command: ["sleep", "5"]}`, если в образе есть `sleep`.

Откат на предыдущую версию — одна команда:

```bash
k rollout undo deployment/hello
# {"pod":"hello-547d6f4788-bbv2p","version":"1.0",...}
```

Если образ не скачивается, новые поды висят в `ErrImagePull`, а старые продолжают работать: Kubernetes не гасит рабочие поды, пока новые не готовы.

## Ресурсы

```yaml
resources:
  requests:        # сколько гарантированно выделить; по этому выбирается машина
    cpu: 50m       # 5% одного ядра
    memory: 64Mi
  limits:
    memory: 128Mi  # превысил — контейнер будет убит (OOMKilled)
```

## Полезные команды

```bash
k get pods,svc,ingress          # что запущено
k describe pod <имя>            # подробности и события: почему не стартует
k logs deployment/hello         # логи
k exec <под> -- printenv GREETING   # команда внутри контейнера
k rollout history deployment/hello
```

## Частые ошибки

- **Тег `latest`.** Kubernetes не поймёт, что образ изменился, и откат станет невозможным: непонятно, на что откатываться. Используйте версию в теге.
- **Secret — это не шифрование.** Значение хранится в base64: `c3VwZXItc2VjcmV0LWtleQ==` за секунду превращается обратно в `super-secret-key`. Ограничивайте доступ к секретам правами (RBAC), включайте шифрование etcd или используйте внешние хранилища вроде Vault.
- **Одна и та же проверка для liveness и readiness с долгим запросом.** Если `/health` проверяет базу, то при сбое базы Kubernetes начнёт перезапускать все поды, и станет только хуже. Liveness должна проверять сам процесс.
- **Нет `requests`.** Kubernetes не знает, сколько ресурсов нужно поду, и может поселить слишком много подов на одну машину.
- **База данных в Deployment.** Для баз с данными на диске есть StatefulSet и PersistentVolume. А часто проще взять управляемую базу у облачного провайдера.
- **Изменения через `kubectl edit` на живом кластере.** Через неделю никто не помнит, что меняли. Храните манифесты в репозитории и применяйте через `kubectl apply` или Helm и ArgoCD.

## Содержание

- [Кластер Kubernetes](docs/cluster.md) — оркестраторы, устройство кластера, локальные кластеры, kubeconfig и контексты, kubectl, namespace, падение узла

## Связанные темы

- [Docker Compose на практике](../../devtools/docker/docs/compose.md)
- [API Gateway на Traefik](../../microservices/api_gateway/README.md)
- [GitHub Actions](../github/README.md) — сборка образов для кластера
- [Portainer](../portainer/README.md) — веб-интерфейс для Docker и Kubernetes
