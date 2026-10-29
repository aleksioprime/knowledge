from rest_framework import serializers

from .models import Tag, Task


class TaskSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    tags = serializers.SlugRelatedField(
        many=True, slug_field='name', queryset=Tag.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = ['id', 'title', 'done', 'priority', 'due_date', 'tags', 'owner', 'created_at']
        read_only_fields = ['created_at']
