from django.contrib import admin
from .models import AITask, AIModel


@admin.register(AITask)
class AITaskAdmin(admin.ModelAdmin):
    list_display = ['user', 'task_type', 'status', 'created_at', 'completed_at']
    list_filter = ['task_type', 'status', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'started_at', 'completed_at']


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'model_id', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active']
    search_fields = ['name', 'model_id'] 