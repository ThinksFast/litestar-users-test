from litestar import Request, get
from litestar.response import Template


@get("/", exclude_from_auth=True)
async def serveHomepage(request: Request) -> Template:
    return Template(
        template_name="index.html.j2",
        context={
            "request": request,
        },
    )


@get("/login", exclude_from_auth=True)
async def serveLogin(request: Request) -> Template:
    return Template(
        template_name="login.html.j2",
        context={
            "request": request,
        },
    )


@get("/top-secret")
async def serveSecretShit(request: Request) -> Template:
    return Template(
        template_name="protected.html.j2",
        context={
            "request": request,
        },
    )
