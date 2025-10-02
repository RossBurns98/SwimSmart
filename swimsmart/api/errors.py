from __future__ import annotations
from typing import Any, Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

def flatten_pydantic_errors(exc: ValidationError) -> List[Dict[str, Any]]:
    """
    Convert pydantic/fastapi error objects into a list of dicts.
    """
    flat: List[Dict[str, Any]] = []
    for err in exc.errors():
        item: Dict[str, Any] = {
            "loc": list(err.get("loc", [])),
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", ""))
        }
        flat.append(item)
    return flat

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach global exception handlers. Leave most HTTPException alone, only 
    customising common erros to keep responses helpful and consistent.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 422 Unprocessable entity, adds clearer payload
        errors = flatten_pydantic_errors(exc)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation failed",
                "errors": errors
            }
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Last-resort
        return JSONResponse(
            status_code=500,
            content={"detail: Internal server error"}
        )