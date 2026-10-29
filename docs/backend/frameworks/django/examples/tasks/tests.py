from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Tag, Task


class TaskApiTests(APITestCase):
    def setUp(self):
        self.anna = User.objects.create_user('anna', password='secret123')
        self.boris = User.objects.create_user('boris', password='secret123')
        Tag.objects.create(name='дом')
        self.client.force_authenticate(self.anna)

    def test_create_and_list(self):
        response = self.client.post('/api/tasks/', {'title': 'Купить хлеб', 'tags': ['дом']}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['owner'], 'anna')
        self.assertEqual(response.data['tags'], ['дом'])

        response = self.client.get('/api/tasks/')
        self.assertEqual(response.data['count'], 1)

    def test_validation(self):
        response = self.client.post('/api/tasks/', {'title': '', 'priority': 10}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {'title', 'priority'})

    def test_foreign_task_is_hidden(self):
        task = Task.objects.create(title='Личное', owner=self.boris)
        response = self.client.get(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, 404)

    def test_partial_update_and_stats(self):
        task = Task.objects.create(title='Сдать отчёт', owner=self.anna, priority=3)
        response = self.client.patch(f'/api/tasks/{task.id}/', {'done': True}, format='json')
        self.assertTrue(response.data['done'])
        self.assertEqual(response.data['priority'], 3)
        self.assertEqual(self.client.get('/api/tasks/stats/').data, {'total': 1, 'done': 1})

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/tasks/').status_code, 403)

    def test_list_without_n_plus_one(self):
        for i in range(10):
            Task.objects.create(title=f'Задача {i}', owner=self.anna).tags.add(Tag.objects.get(name='дом'))
        # count для пагинации, задачи вместе с владельцем (JOIN) и метки всех задач одним запросом
        with self.assertNumQueries(3):
            self.client.get('/api/tasks/')
