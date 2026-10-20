import math

from rest_framework import serializers

from .models import Result, Sample, SampleStatus


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = ["sample_id", "order_id", "client_id", "status"]
        read_only_fields = ["status"]


class SampleStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SampleStatus.choices)


class ResultSerializer(serializers.ModelSerializer):
    result_id = serializers.IntegerField(source="id", read_only=True)
    sample_id = serializers.SlugRelatedField(
        source="sample",
        slug_field="sample_id",
        queryset=Sample.objects.all(),
        error_messages={"does_not_exist": "Sample '{value}' does not exist."},
    )

    class Meta:
        model = Result
        fields = ["result_id", "sample_id", "parameter", "value", "unit", "status"]
        read_only_fields = ["status"]
        extra_kwargs = {"unit": {"required": False, "allow_blank": True}}

    def validate_value(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Value must be a finite number.")
        return value
