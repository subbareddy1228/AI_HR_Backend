from fastapi import Request
from fastapi.responses import JSONResponse

ADMIN_PASSWORD = "Admin@123"

async def admin_auth_middleware(request: Request, call_next):
    path = request.url.path

    # FORCE block everything under /admin
    if path.startswith("/admin"):
        header_pw = request.headers.get("x-admin-password")

        if header_pw != ADMIN_PASSWORD:
            return JSONResponse(
                status_code=403,
                content={"detail": "Admin password required"}
            )

    return await call_next(request)
