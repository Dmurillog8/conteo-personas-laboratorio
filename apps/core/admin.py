from django.contrib import admin

from .models import Laboratory


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "capacity", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "location")
