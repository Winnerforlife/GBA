from django.db import models


class SampleStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ResultStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"


class Sample(models.Model):
    sample_id = models.CharField(max_length=64, unique=True)
    order_id = models.CharField(max_length=64, db_index=True)
    client_id = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=SampleStatus.choices,
        default=SampleStatus.REGISTERED,
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=SampleStatus.values),
                name="sample_status_valid",
            ),
        ]

    def __str__(self):
        return self.sample_id


class Result(models.Model):
    sample = models.ForeignKey(
        Sample,
        on_delete=models.PROTECT,
        related_name="results",
    )
    parameter = models.CharField(max_length=128)
    value = models.FloatField()
    unit = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16,
        choices=ResultStatus.choices,
        default=ResultStatus.DRAFT,
    )

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["sample", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ResultStatus.values),
                name="result_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.sample.sample_id} / {self.parameter}"
