from django.contrib import admin

from .models import CrossingEvent, MonitoringSession, OccupancySample, Snapshot


class OccupancySampleInline(admin.TabularInline):
    model = OccupancySample
    extra = 0
    readonly_fields = ("captured_at", "occupancy", "entries", "exits", "fps")
    can_delete = False
    max_num = 0


@admin.register(MonitoringSession)
class MonitoringSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "laboratory",
        "source_type",
        "status",
        "started_at",
        "ended_at",
        "peak_occupancy",
        "total_entries",
        "total_exits",
    )
    list_filter = ("status", "source_type", "detection_mode", "laboratory")
    search_fields = ("source_label", "laboratory__name", "created_by__username")
    date_hierarchy = "started_at"
    readonly_fields = (
        "started_at",
        "ended_at",
        "peak_occupancy",
        "current_occupancy",
        "total_entries",
        "total_exits",
        "unique_visitors",
    )
    inlines = [OccupancySampleInline]


@admin.register(CrossingEvent)
class CrossingEventAdmin(admin.ModelAdmin):
    list_display = ("session", "occurred_at", "direction", "track_id")
    list_filter = ("direction",)
    date_hierarchy = "occurred_at"


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("session", "occupancy", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
