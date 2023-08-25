"""Handle exceptions gracefully"""
from typing import Callable

from litestar import Request
from litestar.response import Redirect, Template
from litestar.status_codes import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR


def http_401(request: Request, exc: Exception) -> Redirect:
    """Redirect unauthorized requests to login"""
    request.logger.warning("🚨 401 Unauthorized Request: Redirecting user to login")

    return Redirect(path="/login", status_code=302)


def http_500(request: Request, exc: Exception) -> Template:
    """Something broke, lets fix it"""
    request.logger.exception(f"🚨 500 ERROR: something broke on {request.url}: {exc}")

    return Template(
        template_name="500.html.j2",
    )


exception_config: dict[int | type[Exception], Callable] = {
    HTTP_401_UNAUTHORIZED: http_401,
    HTTP_500_INTERNAL_SERVER_ERROR: http_500,
}
