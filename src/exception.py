"""Handle exceptions gracefully"""
from typing import Callable

from litestar import Request
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_401_UNAUTHORIZED,
)


def http_401(request: Request, exc: Exception) -> Redirect:
    """Redirect unauthorized requests to login"""
    request.logger.warning("🚨 401 Unauthorized Request: Redirecting user to login")

    return Redirect(path="/login", status_code=302)


exception_config: dict[int | type[Exception], Callable] = {
    HTTP_401_UNAUTHORIZED: http_401
}
