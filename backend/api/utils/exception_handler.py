from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):

    response = drf_exception_handler(exc, context)

    if response is None:
        return response

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
