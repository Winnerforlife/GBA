from django.db import transaction

from .exceptions import StatusConflict
from .models import Result, ResultStatus, Sample, SampleStatus

# Allowed sample status transitions. `completed` and `cancelled` are final.
ALLOWED_SAMPLE_TRANSITIONS: dict[str, set[str]] = {
    SampleStatus.REGISTERED: {SampleStatus.IN_PROGRESS, SampleStatus.CANCELLED},
    SampleStatus.IN_PROGRESS: {SampleStatus.COMPLETED, SampleStatus.CANCELLED},
    SampleStatus.COMPLETED: set(),
    SampleStatus.CANCELLED: set(),
}

# Results can only be added or approved while the sample is still "open".
OPEN_SAMPLE_STATUSES = {SampleStatus.REGISTERED, SampleStatus.IN_PROGRESS}


def change_sample_status(sample: Sample, new_status: str) -> Sample:
    """Move a sample to `new_status` or raise StatusConflict if the transition is not allowed."""
    if new_status == sample.status:
        raise StatusConflict(f"Sample is already '{sample.status}'.")

    if new_status not in ALLOWED_SAMPLE_TRANSITIONS[sample.status]:
        allowed = sorted(ALLOWED_SAMPLE_TRANSITIONS[sample.status])
        hint = f"Allowed: {', '.join(allowed)}." if allowed else "This status is final."
        raise StatusConflict(
            f"Cannot change sample status from '{sample.status}' to '{new_status}'. {hint}"
        )

    sample.status = new_status
    sample.save(update_fields=["status"])
    return sample


def _ensure_sample_is_open(sample: Sample, action: str) -> None:
    if sample.status not in OPEN_SAMPLE_STATUSES:
        raise StatusConflict(
            f"Cannot {action} for sample '{sample.sample_id}': it is '{sample.status}'."
        )


@transaction.atomic
def create_result(
    *, sample: Sample, parameter: str, value: float, unit: str = ""
) -> Result:
    """Add a draft result to an open sample."""
    sample = Sample.objects.select_for_update().get(pk=sample.pk)
    _ensure_sample_is_open(sample, "add a result")
    return Result.objects.create(
        sample=sample, parameter=parameter, value=value, unit=unit
    )


@transaction.atomic
def approve_result(result: Result) -> Result:
    """Approve a draft result. Approving twice, or on a closed sample, is a conflict."""
    result = (
        Result.objects.select_for_update().select_related("sample").get(pk=result.pk)
    )
    if result.status == ResultStatus.APPROVED:
        raise StatusConflict(f"Result {result.pk} is already approved.")
    _ensure_sample_is_open(result.sample, "approve a result")

    result.status = ResultStatus.APPROVED
    result.save(update_fields=["status"])
    return result
