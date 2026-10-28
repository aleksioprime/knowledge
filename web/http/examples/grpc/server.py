from concurrent import futures

import grpc

import tasks_pb2
import tasks_pb2_grpc


class TaskService(tasks_pb2_grpc.TaskServiceServicer):
    def __init__(self):
        self.tasks: dict[int, tasks_pb2.Task] = {
            1: tasks_pb2.Task(id=1, title='Купить хлеб', done=True, labels=['дом']),
            2: tasks_pb2.Task(id=2, title='Сдать отчёт', labels=['работа']),
        }

    def GetTask(self, request, context):
        task = self.tasks.get(request.id)
        if task is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f'Задача {request.id} не найдена')
        return task

    def ListTasks(self, request, context):
        tasks = [task for task in self.tasks.values() if not (request.only_open and task.done)]
        if request.limit:
            tasks = tasks[: request.limit]
        return tasks_pb2.ListTasksResponse(tasks=tasks)

    def CreateTask(self, request, context):
        if not request.title.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'Название не может быть пустым')
        task_id = max(self.tasks, default=0) + 1
        task = tasks_pb2.Task(id=task_id, title=request.title, labels=request.labels)
        self.tasks[task_id] = task
        return task


def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tasks_pb2_grpc.add_TaskServiceServicer_to_server(TaskService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print('gRPC-сервер слушает порт 50051')
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
