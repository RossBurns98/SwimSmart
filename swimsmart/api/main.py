from fastapi import FastAPI
from swimsmart.api.routes import sessions as session_routes

def create_app() -> FastAPI:
    """
    Build the FastAPI app and register all routers
    """
    app = FastAPI(title="SwimSmart API", version="0.1.0")

    #route registration
    app.include_router(
        session_routes.router,
        prefix="/sessions",
        tags=["sessions"],
    )
    return app

    # entrypoint for uvicorn
    app = create_app()
    