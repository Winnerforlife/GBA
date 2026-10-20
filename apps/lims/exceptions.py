from rest_framework import status
from rest_framework.exceptions import APIException


class StatusConflict(APIException):
    """The requested change is valid input, but not allowed in the current state."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested status change is not allowed."
    default_code = "status_conflict"
