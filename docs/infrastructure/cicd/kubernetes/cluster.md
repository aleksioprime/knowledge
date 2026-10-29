# Кластер Kubernetes: оркестраторы, локальные кластеры, kubeconfig и kubectl

Пока «Задачник» живёт на одном сервере, хватает Docker Compose. Когда серверов становится три, появляются вопросы, которые Compose не решает: на какую машину поставить новую копию API, кто перезапустит воркер после падения сервера, как обновить версию без простоя. Эти вопросы решает оркестратор. Заметка о том, какие оркестраторы бывают, как устроен кластер Kubernetes, как поднять его у себя и как не перепутать локальный кластер с продакшеном.

Базовые объекты (Deployment, Service, Ingress, пробы, обновления) разобраны в [основной заметке про Kubernetes](README.md), здесь — то, что вокруг них.

## Минимальный пример

Кластер из трёх узлов на kind: каждый узел — Docker-контейнер. Конфиг лежит рядом: [kind-cluster.yaml](kind-cluster.yaml).

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: kb-k8s
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

```bash
export KUBECONFIG=$PWD/kubeconfig     # отдельный файл, ~/.kube/config не трогаем
kind create cluster --config kind-cluster.yaml
kubectl get nodes -o wide
# NAME                   STATUS   ROLES           VERSION   INTERNAL-IP   OS-IMAGE                       CONTAINER-RUNTIME
# kb-k8s-control-plane   Ready    control-plane   v1.37.0   172.21.0.4    Debian GNU/Linux 13 (trixie)   containerd://2.3.4
# kb-k8s-worker          Ready    <none>          v1.37.0   172.21.0.3    Debian GNU/Linux 13 (trixie)   containerd://2.3.4
# kb-k8s-worker2         Ready    <none>          v1.37.0   172.21.0.2    Debian GNU/Linux 13 (trixie)   containerd://2.3.4

kind delete cluster --name kb-k8s     # убрать всё
```

Проверено на kind v0.33.0 (по умолчанию он берёт образ `kindest/node:v1.37.0`) и kubectl v1.37.0 в Docker Desktop на macOS. Создание кластера заняло около 6 минут, почти всё время — скачивание образа узла; повторный запуск быстрее. Колонки `AGE`, `EXTERNAL-IP` и `KERNEL-VERSION` в выводе выше убраны для ширины.

## Зачем нужен оркестратор

Оркестратор получает описание «что должно работать» и сам решает, где и как это запустить. Обычно он умеет:

- **размещать** контейнеры по машинам с учётом свободных процессора и памяти;
- **перезапускать** упавшие контейнеры и переносить их с отказавшей машины на живые;
- **масштабировать**: было 2 копии API, стало 6, по команде или по нагрузке;
- **обновлять без простоя**: заменять копии по одной и откатывать, если новая версия не поднялась;
- **находить сервисы и балансировать**: API обращается к `redis` по имени, а оркестратор знает, где сейчас этот redis и сколько у него копий;
- **раздавать конфигурацию и секреты** контейнерам.

Чего оркестратор не делает. Он запускает контейнеры, но не даёт вам надёжную базу, брокер или хранилище: PostgreSQL в кластере остаётся вашей заботой (резервные копии, реплики, обновления), и часто проще взять управляемую базу у облака. И он не проектирует систему: если сервис хранит состояние в памяти процесса, шесть копий за балансировщиком будут отвечать по-разному.

### Контейнер — не виртуальная машина

Оркестратор раздаёт по машинам контейнеры, поэтому полезно помнить, чем они отличаются от виртуальных машин (подробнее — в разделе [«Как Docker устроен внутри»](../../devtools/docker/README.md#как-docker-устроен-внутри)):

- у контейнеров **общее ядро** хоста. Отсюда быстрый старт и малые накладные расходы;
- **изоляция слабее**: соседи влияют друг на друга через общие ресурсы ядра (кеш страниц, диск, сеть, таблицы conntrack), а уязвимость ядра затрагивает все контейнеры на машине. Чужой недоверенный код обычно запускают в виртуальных машинах или песочницах (gVisor, Kata Containers);
- на Linux-хосте **не запустить Windows-контейнер** и наоборот: ядро одно, и оно определяет, какие программы в контейнере вообще могут работать.

## Какие бывают оркестраторы

| | Docker Swarm | HashiCorp Nomad | Kubernetes | Apache Mesos + Marathon |
|---|---|---|---|---|
| Сложность эксплуатации | Низкая: встроен в Docker Engine, `docker swarm init` | Средняя: один бинарник, но service discovery и секреты — через Consul и Vault | Высокая: много компонентов, но есть управляемые сервисы в облаках | Высокая |
| Что умеет | Сервисы, реплики, rolling update, оверлейная сеть, секреты; описание в формате Compose (`docker stack deploy`) | Контейнеры и не только: обычные процессы, Java, виртуальные машины; пакетные задачи | Всё из списка выше плюс автомасштабирование, сетевые политики, RBAC, операторы и огромная экосистема (Helm, ArgoCD, Prometheus) | Двухуровневое планирование: Mesos делит ресурсы, фреймворки (Marathon, Spark) запускают задачи |
| Лицензия и статус на 2026-10 | Swarm mode — часть Docker Engine, в документации без пометки об устаревании. Mirantis обещает поддержку Swarm в MKE 3 как минимум до 2030 года | Business Source License 1.1 начиная с Nomad 1.7.0 (смена лицензии в августе 2023), каждая версия через 4 года переходит в MPL 2.0 | Apache 2.0, проект CNCF | Mesos перенесён в Apache Attic: проект закрыт в августе 2025, переезд завершён в октябре 2025 |
| Когда выбрать | Несколько машин, команда знает Compose, нужна простота | Смешанная нагрузка (не только контейнеры), уже есть Consul и Vault | Стандарт по умолчанию, особенно с управляемым кластером в облаке | Для новых проектов — нет |

Пределы размера. Для Kubernetes официальная страница [Considerations for large clusters](https://kubernetes.io/docs/setup/best-practices/cluster-large/) (версия 1.37) называет не больше 5 000 узлов, 110 подов на узел, 150 000 подов и 300 000 контейнеров в кластере. Для остальных оркестраторов официальных цифр в документации нет, поэтому они здесь не приводятся.

Что не удалось подтвердить: точный статус Marathon. Проект давно не развивается, но дата архивации по официальному источнику не проверялась. Лицензия Nomad подтверждена по файлу `LICENSE` в репозитории `hashicorp/nomad`; что BSL применяется с версии 1.7.0 — из того же файла.

## Как устроен кластер Kubernetes

Кластер делится на **управляющую часть (control plane)** и **рабочие узлы (worker nodes)**.

**Control plane** принимает решения:

- **API server** (`kube-apiserver`) — единственная входная дверь. `kubectl`, контроллеры, kubelet на узлах — все общаются только с ним;
- **etcd** — распределённое хранилище ключ-значение, где лежит всё состояние кластера. Потеря etcd без резервной копии — потеря кластера;
- **scheduler** (`kube-scheduler`) выбирает узел для нового пода по ресурсам, меткам и правилам размещения;
- **controller manager** (`kube-controller-manager`) — набор контроллеров: следит, чтобы у Deployment было нужное число подов, отмечает недоступные узлы, выселяет с них поды.

**Рабочий узел** выполняет:

- **kubelet** — агент на узле: получает от API server список подов для своей машины, запускает их и докладывает о состоянии;
- **kube-proxy** — настраивает правила iptables или IPVS, чтобы обращение к Service попадало на один из его подов;
- **среда выполнения контейнеров** — containerd или CRI-O. kubelet говорит с ней через интерфейс CRI (Container Runtime Interface). Прослойку dockershim, через которую kubelet работал с Docker Engine напрямую, удалили в Kubernetes 1.24. Образы, собранные `docker build`, при этом работают как раньше: формат образа общий (OCI).

В kind все компоненты control plane видны как поды в `kube-system`:

```bash
kubectl get pods -n kube-system -o wide
# NAME                                           READY   STATUS    IP           NODE
# coredns-559f6c778d-lf5zf                       1/1     Running   10.244.0.3   kb-k8s-control-plane
# coredns-559f6c778d-n5hgj                       1/1     Running   10.244.0.2   kb-k8s-control-plane
# etcd-kb-k8s-control-plane                      1/1     Running   172.21.0.4   kb-k8s-control-plane
# kindnet-77pq5                                  1/1     Running   172.21.0.3   kb-k8s-worker
# kindnet-nhs6z                                  1/1     Running   172.21.0.2   kb-k8s-worker2
# kindnet-z7cl7                                  1/1     Running   172.21.0.4   kb-k8s-control-plane
# kube-apiserver-kb-k8s-control-plane            1/1     Running   172.21.0.4   kb-k8s-control-plane
# kube-controller-manager-kb-k8s-control-plane   1/1     Running   172.21.0.4   kb-k8s-control-plane
# kube-proxy-79vf2                               1/1     Running   172.21.0.3   kb-k8s-worker
# kube-proxy-9fpmq                               1/1     Running   172.21.0.2   kb-k8s-worker2
# kube-proxy-mv8wk                               1/1     Running   172.21.0.4   kb-k8s-control-plane
# kube-scheduler-kb-k8s-control-plane            1/1     Running   172.21.0.4   kb-k8s-control-plane
```

`etcd`, `kube-apiserver`, `kube-scheduler`, `kube-controller-manager` — по одному, на управляющем узле. `kube-proxy` и сетевой плагин `kindnet` — на каждом узле. `coredns` — DNS кластера, благодаря ему сервис доступен по имени. kubelet в списке нет: это обычный процесс на узле, а не под.

Здоровье API server можно спросить у него самого:

```bash
kubectl get --raw '/readyz?verbose'
# [+]ping ok
# [+]log ok
# [+]etcd ok
# [+]etcd-readiness ok
# [+]informer-sync ok
# [+]poststarthook/start-apiserver-admission-initializer ok
# ...
# [+]poststarthook/rbac/bootstrap-roles ok
# ...
# [+]shutdown ok
# readyz check passed
```

### Pod — не контейнер

**Pod** — группа из одного или нескольких контейнеров, которые всегда стоят на одном узле, делят один IP-адрес и могут делить тома. Контейнеры одного пода общаются через `localhost`. Обычно в поде один контейнер с приложением, иногда рядом вспомогательный (sidecar): прокси, сборщик логов. Планировщик размещает именно поды, а не отдельные контейнеры.

### Желаемое состояние

Kubernetes декларативный. Вы не говорите «запусти ещё два пода», вы записываете в манифест «должно быть четыре пода» и отправляете его в API server (`kubectl apply`). Описание сохраняется в etcd, а контроллеры в бесконечном цикле сравнивают желаемое с текущим и устраняют разницу. Поэтому удалённый под возвращается сам, а ручная правка живого объекта тихо перетирается следующим `apply` из репозитория.

## Что будет, если узел упал

Deployment «Задачника» на 4 реплики в namespace `tasker` распределился по двум рабочим узлам поровну. На управляющий узел поды не попадают: на нём стоит запрет (taint) `node-role.kubernetes.io/control-plane:NoSchedule`.

```bash
kubectl config use-context tasker
kubectl create deployment tasker-api --image=traefik/whoami:v1.10 --replicas=4
kubectl get pods -o wide
# NAME                          READY   STATUS    IP           NODE
# tasker-api-568d7577bc-2zdtk   1/1     Running   10.244.2.6   kb-k8s-worker
# tasker-api-568d7577bc-q599f   1/1     Running   10.244.1.6   kb-k8s-worker2
# tasker-api-568d7577bc-qqjvw   1/1     Running   10.244.2.7   kb-k8s-worker
# tasker-api-568d7577bc-r65r8   1/1     Running   10.244.1.7   kb-k8s-worker2
```

«Уроним» первый рабочий узел — остановим его контейнер — и будем каждые 5 секунд смотреть на узел и поды:

```bash
docker stop kb-k8s-worker
# t=1s    узел Ready, 4 пода Running: 2 на worker, 2 на worker2
# t=58s   узел NotReady, поды на worker по-прежнему числятся Running
# t=357s  на worker2 созданы 2 новых пода, старые 2 помечены Terminating
kubectl get pods -o wide
# tasker-api-568d7577bc-26ghp   1/1   Running       3s      kb-k8s-worker2
# tasker-api-568d7577bc-2zdtk   1/1   Terminating   6m13s   kb-k8s-worker
# tasker-api-568d7577bc-q599f   1/1   Running       6m13s   kb-k8s-worker2
# tasker-api-568d7577bc-qqjvw   1/1   Terminating   6m11s   kb-k8s-worker
# tasker-api-568d7577bc-r65r8   1/1   Running       6m12s   kb-k8s-worker2
# tasker-api-568d7577bc-zln5v   1/1   Running       3s      kb-k8s-worker2
```

Поды переехали почти через **6 минут**, и это поведение по умолчанию, а не поломка. Оно складывается из двух задержек:

1. **Около 50 секунд — узел признают недоступным.** kubelet регулярно отмечается у API server. Если отметок нет дольше `node-monitor-grace-period` (по умолчанию 50 секунд, параметр `kube-controller-manager`), узел получает статус `NotReady`, а контроллер ставит на него запреты (taints) `node.kubernetes.io/unreachable` с эффектами `NoSchedule` (новые поды сюда не планировать) и `NoExecute` (выселять работающие).
2. **300 секунд — поды терпят этот запрет.** Каждому поду при создании автоматически добавляются допуски (tolerations):

```bash
kubectl get pod <имя> -o jsonpath='{.spec.tolerations}'
# [{"effect":"NoExecute","key":"node.kubernetes.io/not-ready","operator":"Exists","tolerationSeconds":300},
#  {"effect":"NoExecute","key":"node.kubernetes.io/unreachable","operator":"Exists","tolerationSeconds":300}]
```

Пять минут — защита от лишних переездов: сеть моргнула на минуту, и гонять поды туда-обратно не стоило. Только после этого контроллер удаляет поды с узла, Deployment видит нехватку реплик и создаёт новые на живом узле.

Для демонстрации задержку можно сократить, задав допуски в шаблоне пода явно:

```yaml
spec:
  template:
    spec:
      tolerations:
        - key: node.kubernetes.io/not-ready
          operator: Exists
          effect: NoExecute
          tolerationSeconds: 10
        - key: node.kubernetes.io/unreachable
          operator: Exists
          effect: NoExecute
          tolerationSeconds: 10
```

С ними повторный опыт дал: `NotReady` на 49-й секунде, новые поды на `worker2` — к 64–71-й секунде. Точность замеров — около 5 секунд, шаг опроса. В продакшене так делать стоит осторожно: короткий допуск превращает каждый сетевой сбой в массовый переезд подов. Надёжнее держать несколько реплик на разных узлах, тогда сервис работает и все эти шесть минут.

Ещё два наблюдения из опыта:

- старые поды висят в `Terminating`, пока узел не вернётся: kubelet на мёртвой машине не может подтвердить, что контейнеры остановлены. Deployment их уже не учитывает, но объект в API остаётся;
- когда узел вернулся, поды **не** вернулись обратно: все 4 так и остались на `worker2`. Kubernetes не перераспределяет работающие поды. Распределение выравнивается при следующем обновлении Deployment (`kubectl rollout restart`) или с помощью отдельного компонента descheduler.

Сетевой нюанс kind: образ `traefik/whoami` пришлось загрузить в узлы с хоста (`kind load`), потому что узлы не могли скачать его сами. Почему — в разделе [«Частые ошибки»](#частые-ошибки).

## Локальные кластеры

| Вариант | Как устроен | Когда выбрать |
|---|---|---|
| Docker Desktop | Встроенный кластер, включается галочкой. Два способа: kubeadm (один узел) и kind (несколько узлов, выбор версии). Контекст `docker-desktop` | Уже стоит Docker Desktop и нужен кластер «просто чтобы был» |
| minikube | Один или несколько узлов в выбранном драйвере: `docker`, `podman`, виртуальные машины (`qemu`, `vfkit`, `hyperkit`, `virtualbox`, `hyperv`) или прямо на хосте (`none`). Много дополнений: `minikube addons enable ingress` | Учиться: есть дополнения и дашборд; нужна виртуальная машина вместо контейнера |
| kind | Каждый узел — Docker-контейнер. Несколько узлов, любая версия Kubernetes через образ `kindest/node` | Тесты в CI, проверка поведения с несколькими узлами, проверка обновления версии |
| k3s / k3d | k3s — облегчённый дистрибутив в одном бинарнике (встроены Traefik, локальное хранилище). k3d запускает k3s в Docker и умеет несколько узлов | Слабая машина, edge-устройства, небольшой продакшен на своих серверах |
| k0s | Дистрибутив в одном бинарнике без зависимостей от ОС | Свои серверы, хочется минимум движущихся частей |
| MicroK8s | Дистрибутив от Canonical, ставится через snap, дополнения включаются командой | Ubuntu-машины, кластер из нескольких серверов без облака |

Общее правило: для изучения и CI — kind или minikube, для небольшого продакшена на своих серверах — k3s или k0s.

Пример k3s в Docker — в [основной заметке](README.md#свой-кластер-за-минуту).

### Управляемый Kubernetes в облаке

В управляемом кластере (EKS, GKE, AKS, Yandex Managed Service for Kubernetes и другие) control plane берёт на себя провайдер: он держит etcd и API server в нескольких копиях, делает резервные копии и обновляет версии. Вам остаются рабочие узлы (часто тоже в виде автоматической группы) и то, что на них запущено. Второй плюс — интеграция: PersistentVolume становится облачным диском, Service типа `LoadBalancer` — облачным балансировщиком с внешним адресом. В локальном кластере для того же нужны дополнения вроде MetalLB или `minikube tunnel`.

## kubeconfig: куда смотрит kubectl

kubectl узнаёт адрес кластера и учётные данные из файла kubeconfig. По умолчанию это `~/.kube/config`. Внутри три списка и указатель:

- **clusters** — адрес API server и сертификат центра сертификации;
- **users** — чем представляться: клиентский сертификат, токен или команда, которая токен получит;
- **contexts** — пара «кластер + пользователь», плюс namespace по умолчанию;
- **current-context** — с каким контекстом работает kubectl прямо сейчас.

```bash
kubectl config view          # секреты заменены на DATA+OMITTED
# clusters:
# - cluster:
#     certificate-authority-data: DATA+OMITTED
#     server: https://127.0.0.1:52426
#   name: kind-kb-k8s
# contexts:
# - context:
#     cluster: kind-kb-k8s
#     namespace: default
#     user: kind-kb-k8s
#   name: kind-kb-k8s
# current-context: kind-kb-k8s
# users:
# - name: kind-kb-k8s
#   user:
#     client-certificate-data: DATA+OMITTED
#     client-key-data: DATA+OMITTED
```

Контекст удобно заводить не только на кластер, но и на namespace. Сделаем второй контекст `tasker` для того же кластера:

```bash
kubectl create namespace tasker
kubectl config set-context tasker --cluster=kind-kb-k8s --user=kind-kb-k8s --namespace=tasker
kubectl config get-contexts
# CURRENT   NAME          CLUSTER       AUTHINFO      NAMESPACE
# *         kind-kb-k8s   kind-kb-k8s   kind-kb-k8s
#           tasker        kind-kb-k8s   kind-kb-k8s   tasker

kubectl config use-context tasker
# Switched to context "tasker".
kubectl get pods
# No resources found in tasker namespace.     ← -n писать не нужно

kubectl config use-context kind-kb-k8s
kubectl config set-context --current --namespace=kube-system   # сменить namespace у текущего контекста
kubectl config get-contexts
# CURRENT   NAME          CLUSTER       AUTHINFO      NAMESPACE
# *         kind-kb-k8s   kind-kb-k8s   kind-kb-k8s   kube-system
#           tasker        kind-kb-k8s   kind-kb-k8s   tasker
```

### Несколько файлов

Переменная `KUBECONFIG` принимает список файлов через `:` (в Windows через `;`). kubectl склеивает их в одну конфигурацию: при совпадении имён побеждает первый файл, `current-context` берётся из первого файла, где он задан. Положим доступ к «продакшену» в отдельный файл:

```bash
export KUBECONFIG=$PWD/kubeconfig:$PWD/prod.yaml
kubectl config get-contexts
# CURRENT   NAME          CLUSTER       AUTHINFO      NAMESPACE
# *         kind-kb-k8s   kind-kb-k8s   kind-kb-k8s   default
#           prod          prod          prod-admin    tasker
#           tasker        kind-kb-k8s   kind-kb-k8s   tasker
```

Слить всё в один файл: `kubectl config view --flatten > merged.yaml` (`--flatten` вставляет сертификаты внутрь, без него будут ссылки на файлы).

`KUBECONFIG` меняет только источник настроек: кеш списка API kubectl всё равно пишет в `~/.kube/cache`, если не задать `--cache-dir` или `KUBECACHEDIR`.

### Как не удалить прод вместо локального кластера

Контекст — глобальное состояние: `use-context` в одном терминале меняет файл, и это видят все остальные терминалы. Вчера переключились на прод посмотреть логи, сегодня `kubectl delete namespace tasker` «на локальном». Что помогает:

- **держать прод в отдельном файле** и подключать его явно, только на время работы: `KUBECONFIG=~/.kube/prod.yaml kubectl ...`. В обычном окружении прод-контекста просто нет;
- **показывать контекст в приглашении shell** (kube-ps1, тема starship или oh-my-zsh), прод — красным;
- **указывать контекст в команде** в скриптах и CI: `kubectl --context kind-kb-k8s ...`;
- **давать на проде права только на чтение** по умолчанию, а изменения проводить через CI или GitOps (ArgoCD);
- утилиты **kubectx** и **kubens** переключают контекст и namespace короче, чем `kubectl config`, и показывают список с подсветкой текущего.

## kubectl

Общий вид команды:

```text
kubectl <команда> <тип> <имя> <флаги>
kubectl get       pods  tasker-api-568d7577bc-2zdtk  -o wide -n tasker
```

Тип пишут полностью, во множественном числе или кратко: `pods`, `pod`, `po`; `deployments`, `deploy`; `services`, `svc`.

Формат вывода:

- `-o wide` — дополнительные колонки: узел, IP;
- `-o yaml` — объект целиком, как его хранит кластер (со `status` и служебными полями);
- `-o jsonpath='{.items[*].spec.nodeName}'` — достать конкретное поле для скрипта.

**Заготовка манифеста.** Писать YAML с нуля не нужно: `--dry-run=client` строит объект, но не отправляет его в кластер.

```bash
kubectl create deployment tasker-api --image=nginx:1.27 --replicas=4 --port=80 \
  --dry-run=client -o yaml > deployment.yaml
cat deployment.yaml
# apiVersion: apps/v1
# kind: Deployment
# metadata:
#   labels:
#     app: tasker-api
#   name: tasker-api
# spec:
#   replicas: 4
#   selector:
#     matchLabels:
#       app: tasker-api
#   strategy: {}
#   template:
#     metadata:
#       labels:
#         app: tasker-api
#     spec:
#       containers:
#       - image: nginx:1.27
#         name: nginx
#         ports:
#         - containerPort: 80
#         resources: {}
# status: {}
```

Пустые `strategy: {}`, `resources: {}` и `status: {}` удаляют, имя контейнера правят, дописывают ресурсы и пробы — и манифест готов к репозиторию.

**Справка по полям** без браузера:

```bash
kubectl explain deployment.spec.replicas
# FIELD: replicas <integer>
# DESCRIPTION:
#     Number of desired pods. This is a pointer to distinguish between explicit
#     zero and not specified. Defaults to 1.
```

**Какие типы объектов есть в кластере**, их краткие имена и группы API — `kubectl api-resources`. Там же видно, какие из них живут в namespace.

### Day-0, Day-1, Day-2

Так называют этапы жизни кластера. **Day-0** — проектирование: где кластер, сколько узлов, какая сеть и хранилище. **Day-1** — установка кластера и первое развёртывание приложений. **Day-2** — эксплуатация: обновления версий, мониторинг, резервные копии etcd, замена узлов, права. Day-2 длится годами и стоит больше всего, поэтому его и отдают облачному провайдеру.

## Namespace

**Namespace** — логическое разделение одного кластера: `tasker-dev` и `tasker-staging` могут жить рядом, и Deployment `tasker-api` в каждом свой. Внутри namespace имена уникальны, между namespace — нет. Сервис из соседнего namespace доступен по имени `tasker-api.tasker-staging.svc.cluster.local`.

Namespace — это ещё и граница для правил:

- **ResourceQuota** ограничивает суммарные ресурсы namespace: не больше 4 CPU и 8 ГБ памяти на всё окружение разработки;
- **LimitRange** задаёт ресурсы по умолчанию для контейнеров без `requests` и `limits`;
- **RBAC**: Role и RoleBinding дают права внутри одного namespace — разработчик может всё в `tasker-dev` и ничего в `tasker-prod`.

Namespace — не изоляция по сети: без NetworkPolicy поды из разных namespace свободно ходят друг к другу.

Не все объекты принадлежат namespace. Узлы, сами namespace, PersistentVolume, StorageClass, ClusterRole — общие для кластера:

```bash
kubectl api-resources --namespaced=false
# NAME                  SHORTNAMES   APIVERSION                        NAMESPACED   KIND
# namespaces            ns           v1                                false        Namespace
# nodes                 no           v1                                false        Node
# persistentvolumes     pv           v1                                false        PersistentVolume
# ...
# customresourcedefinitions   crd,crds   apiextensions.k8s.io/v1      false        CustomResourceDefinition
# ...
```

В кластере kind 1.37 таких типов 37, а принадлежащих namespace — 34.

## Частые ошибки

- **Команда ушла не в тот кластер.** Текущий контекст остался от вчерашней работы с продом → удалили или перезаписали не то. Держать прод в отдельном kubeconfig, контекст в приглашении shell, `--context` в скриптах.
- **Ресурс «пропал».** `kubectl get pods` пуст, хотя Deployment создавали → объект в другом namespace. `kubectl get pods -A` показывает все namespace, а `kubectl config get-contexts` — какой namespace выбран сейчас.
- **Под в `ImagePullBackOff` в локальном кластере.** У kind и k3s своё хранилище образов, локальный `docker build` им не виден → загрузить образ: `kind load docker-image <образ> --name kb-k8s`. В Docker Desktop с хранилищем образов containerd эта команда падала с `content digest ... not found` для многоплатформенного образа; помогло сохранить одну платформу: `docker save --platform linux/arm64 <образ> -o img.tar && kind load image-archive img.tar --name kb-k8s`.
- **Узлы kind не скачивают образы, а хост скачивает.** kind передаёт узлам переменные `HTTP_PROXY`/`HTTPS_PROXY` из окружения, в котором его запустили. Если прокси слушает `127.0.0.1` хоста, внутри узла по этому адресу никого нет: `proxyconnect tcp: dial tcp 127.0.0.1:...: connect: connection refused`. Проверить: `docker exec kb-k8s-worker env | grep -i proxy`. Создавать кластер без этих переменных или с прокси, доступным из контейнеров.
- **Ожидание, что поды с упавшего узла переедут мгновенно.** По умолчанию это около 50 секунд плюс 300 секунд допуска, в опыте выше — почти 6 минут → для быстрого переключения нужны несколько реплик на разных узлах, а не быстрый переезд.
- **Kubernetes ради одного сервера.** Кластер из одного узла не даёт отказоустойчивости, но добавляет сложность → на одной машине оставаться на Compose.
- **Ручная правка в кластере вместо манифеста в репозитории.** Следующий `kubectl apply` из CI вернёт старое значение → менять манифест и применять его.

## Когда не использовать

- **Одна машина.** Docker Compose проще, а отказоустойчивости кластер из одного узла не добавит. Перезапуск после сбоя даёт `restart: unless-stopped`.
- **Маленькая команда без человека, который будет заниматься эксплуатацией.** Day-2 у Kubernetes дорогой. Лучше управляемый Kubernetes, где control plane не ваша забота, или PaaS (Render, Fly.io, облачные контейнерные сервисы), где нет даже узлов.
- **Несколько машин, простые сервисы, команда знает Compose.** Docker Swarm разворачивается за минуты из тех же compose-файлов.

## Связанные темы

- [Kubernetes](README.md) — Deployment, Service, Ingress, пробы, обновление без простоя на k3s
- [Docker: как устроен внутри](../../devtools/docker/README.md#как-docker-устроен-внутри) — namespaces, cgroups, слои
- [Docker Compose на практике](../../devtools/docker/compose.md)
- [Portainer](../portainer/README.md) — веб-интерфейс, умеет подключаться к Kubernetes
- [GitHub Actions](../github/README.md) — кластер kind удобно поднимать прямо в CI
