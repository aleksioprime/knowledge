from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Tag(models.Model):
    name = models.CharField('название', max_length=50, unique=True)

    class Meta:
        verbose_name = 'метка'
        verbose_name_plural = 'метки'

    def __str__(self):
        return self.name


class Task(models.Model):
    title = models.CharField('название', max_length=200)
    done = models.BooleanField('выполнена', default=False)
    priority = models.PositiveSmallIntegerField(
        'приоритет', default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    due_date = models.DateField('срок', null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks', verbose_name='владелец'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks', verbose_name='метки')
    created_at = models.DateTimeField('создана', auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'задача'
        verbose_name_plural = 'задачи'

    def __str__(self):
        return self.title
