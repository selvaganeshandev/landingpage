import threading

_thread_locals = threading.local()

def get_current_request():
    """Retrieve the current Django request object from thread-local storage."""
    return getattr(_thread_locals, 'request', None)

def get_current_org_id():
    """Retrieve the organisation ID of the user associated with the current request."""
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user:
        if hasattr(request.user, 'organisation_id') and request.user.organisation_id:
            return request.user.organisation_id
        if hasattr(request.user, 'organisation') and request.user.organisation:
            return request.user.organisation.id
    return None

class ThreadLocalRequestMiddleware:
    """Middleware that stores the current request in thread-local storage."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            if hasattr(_thread_locals, 'request'):
                del _thread_locals.request
