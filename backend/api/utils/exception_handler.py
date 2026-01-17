import logging

from django.db import DatabaseError, OperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):

    response = drf_exception_handler(exc, context)

    if response is None:
        if isinstance(exc, (DatabaseError, OperationalError)):
            logger.exception("Database error")
            return Response(
                {"error": "Database error, please retry."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        logger.exception("Unhandled exception")
        return Response(
            {"error": "Internal server error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normalize response.data into {"error": ...}
    data = response.data

    # If DRF provided a dict with 'detail', use that message
    if isinstance(data, dict):
        if 'detail' in data:
            message = data['detail']
        else:
            # keep field errors as-is (validation errors)
            message = data
    else:
        message = data

    response.data = {"error": message}
    return response
