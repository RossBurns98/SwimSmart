import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi


from swimsmart.api.routes import sessions as session_routes
from swimsmart.api.routes import auth as auth_routes
from swimsmart.api.routes import coach as coach_routes
from swimsmart.api.routes import me as me_routes
from swimsmart.api.routes import exports as export_routes
from swimsmart.api.errors import register_exception_handlers
from dotenv import load_dotenv

load_dotenv()

def _parse_origins(env_value: str | None) -> list[str]:
    """
    Parse comma-separated origins from env; fallback to ["*"] if unset/blank.
    """
    if not env_value:
        return ["*"]
    # support JSON-style list or comma-separated list
    v = env_value.strip()
    if v.startswith("[") and v.endswith("]"):
        try:
            import json
            parsed = json.loads(v)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except Exception:
            pass
    return [o.strip() for o in v.split(",") if o.strip()]

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="SwimSmart API",
        version="1.0.0",
        description="API docs",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def create_app() -> FastAPI:
    """
    Build the FastAPI app and register all routers
    """
    app_version = os.getenv("SWIMSMART_VERSION", "0.1.0")
    app_env = os.getenv("SWIMSMART_ENV", "development")
    cors_origins = _parse_origins(os.getenv("SWIMSMART_CORS_ORIGINS"))

    app = FastAPI(title="SwimSmart API", version=app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,   # env-configurable; defaults to ["*"]
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    register_exception_handlers(app)

    
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # System endpoints (for ops / deployment checks)
    @app.get("/system/health")
    def system_health() -> dict:
        return {"status": "ok"}

    @app.get("/system/version")
    def system_version() -> dict:
        return {"version": app_version, "env": app_env}

    # Route registration
    app.include_router(session_routes.router, prefix="/sessions", tags=["sessions"])
    app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
    app.include_router(coach_routes.router, prefix="/coach", tags=["coach"])
    app.include_router(me_routes.router, prefix="/me", tags=["me"])
    app.include_router(export_routes.router, prefix="/export", tags=["export"])

    app.openapi = lambda: custom_openapi(app)

    return app


# entrypoint for uvicorn
app = create_app()
