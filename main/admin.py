from django.contrib import admin
from .models import (
    RepairRequest, Service, StockPart,
    RepairStatusHistory, RepairComment, RepairPartUsage,
)


@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer_name', 'phone', 'device', 'status',
        'assigned_master', 'labor_cost', 'created_at',
    )
    list_filter = ('status', 'created_at', 'assigned_master')
    search_fields = ('customer_name', 'phone', 'device', 'problem')
    autocomplete_fields = ('user', 'assigned_master', 'service')
    readonly_fields = ('created_at',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'duration', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)


@admin.register(StockPart)
class StockPartAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'quantity', 'min_quantity',
        'price', 'supplier', 'is_low_stock',
    )
    list_filter = ('category',)
    search_fields = ('name', 'supplier')
    readonly_fields = ('created_at',)


@admin.register(RepairStatusHistory)
class RepairStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('repair', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')
    readonly_fields = ('repair', 'old_status', 'new_status', 'comment', 'changed_by', 'created_at')


@admin.register(RepairComment)
class RepairCommentAdmin(admin.ModelAdmin):
    list_display = ('repair', 'author', 'created_at')
    search_fields = ('text', 'repair__customer_name')
    readonly_fields = ('repair', 'author', 'text', 'created_at')


@admin.register(RepairPartUsage)
class RepairPartUsageAdmin(admin.ModelAdmin):
    list_display = ('repair', 'part', 'quantity', 'unit_price', 'used_by', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('repair', 'part', 'quantity', 'unit_price', 'used_by', 'created_at')
