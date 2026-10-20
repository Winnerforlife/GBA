from .exceptions import StatusConflict
from .models import Sample, SampleStatus

# Allowed sample status transitions. `completed` and `cancelled` are final.
ALLOWED_SAMPLE_TRANSITIONS: dict[str, set[str]] = {
    SampleStatus.REGISTERED: {SampleStatus.IN_PROGRESS, SampleStatus.CANCELLED},
    SampleStatus.IN_PROGRESS: {SampleStatus.COMPLETED, SampleStatus.CANCELLED},
    SampleStatus.COMPLETED: set(),
    SampleStatus.CANCELLED: set(),
}


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
