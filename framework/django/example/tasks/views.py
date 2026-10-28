from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        # Только свои задачи: чужие для пользователя просто не существуют (404)
        queryset = Task.objects.filter(owner=self.request.user).select_related('owner').prefetch_related('tags')
        done = self.request.query_params.get('done')
        if done is not None:
            queryset = queryset.filter(done=done.lower() == 'true')
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False)
    def stats(self, request):
        stats = Task.objects.filter(owner=request.user).aggregate(
            total=Count('id'), done=Count('id', filter=Q(done=True))
        )
        return Response(stats)
