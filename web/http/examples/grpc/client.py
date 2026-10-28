import grpc

import tasks_pb2
import tasks_pb2_grpc

with grpc.insecure_channel('localhost:50051') as channel:
    stub = tasks_pb2_grpc.TaskServiceStub(channel)

    created = stub.CreateTask(tasks_pb2.CreateTaskRequest(title='Позвонить врачу', labels=['здоровье']))
    print('Создана:', created.id, created.title, list(created.labels))

    task = stub.GetTask(tasks_pb2.GetTaskRequest(id=created.id), timeout=2)
    print('Получена:', task.id, task.title, 'выполнена' if task.done else 'открыта')

    response = stub.ListTasks(tasks_pb2.ListTasksRequest(only_open=True))
    print('Открытые:', [t.title for t in response.tasks])

    print('Размер сообщения:', len(task.SerializeToString()), 'байт')

    try:
        stub.GetTask(tasks_pb2.GetTaskRequest(id=999))
    except grpc.RpcError as error:
        print('Ошибка:', error.code().name, '-', error.details())

    try:
        stub.CreateTask(tasks_pb2.CreateTaskRequest(title='  '))
    except grpc.RpcError as error:
        print('Ошибка:', error.code().name, '-', error.details())
