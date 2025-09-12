from fastapi import FastAPI
from swimsmart.api.routes import sessions as session_routes
from fastapi.middleware.cors import CORSMiddleware
from swimsmart.api.routes import auth as auth_routes


def create_app() -> FastAPI:
    """
    Build the FastAPI app and register all routers
    """
    app = FastAPI(title="SwimSmart API", version="0.1.0")

    app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )
    
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    #route registration
    app.include_router(
        session_routes.router,
        prefix="/sessions",
        tags=["sessions"],
    )

    app.include_router(
        auth_routes.router,
        prefix="/auth",
        tags=["auth"],
    )
    return app

    # entrypoint for uvicorn
    app = create_app()
    