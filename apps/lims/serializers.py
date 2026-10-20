from rest_framework import serializers

from .models import Sample, SampleStatus


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = ["sample_id", "order_id", "client_id", "status"]
        read_only_fields = ["status"]


class SampleStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SampleStatus.choices)
