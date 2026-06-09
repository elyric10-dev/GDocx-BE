from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import api_router
from app.services.supabase_retry import is_transient_supabase_error

app = FastAPI(
    title="GDocx API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc

    if is_transient_supabase_error(exc):
        detail = "Database temporarily unavailable. Please retry."
    else:
        detail = "An unexpected error occurred. Please retry."

    return JSONResponse(
        status_code=503,
        content={"detail": detail},
    )


app.include_router(api_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "GDocx API", "docs": "/api/docs"}
