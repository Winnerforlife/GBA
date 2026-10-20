from django.contrib import admin

from .models import Result, Sample


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "order_id", "client_id", "status")
    list_filter = ("status",)
    search_fields = ("sample_id", "order_id", "client_id")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("id", "sample", "parameter", "value", "unit", "status")
    list_filter = ("status",)
    search_fields = ("sample__sample_id", "parameter")
