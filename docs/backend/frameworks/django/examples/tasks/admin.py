from django.contrib import admin

from .models import Tag, Task


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'priority', 'due_date', 'done']
    list_filter = ['done', 'priority', 'tags']
    list_editable = ['done']
    search_fields = ['title', 'owner__username']
    date_hierarchy = 'due_date'
    filter_horizontal = ['tags']
    list_select_related = ['owner']
    actions = ['mark_done']

    @admin.action(description='Отметить выполненными')
    def mark_done(self, request, queryset):
        updated = queryset.update(done=True)
        self.message_user(request, f'Отмечено задач: {updated}')
