"""HTTP transport for the host's validated problem and run controls."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .catalog import default_configuration
from .meals import MealProblem
from .models import EvaluateRequest
from .runs import router as run_router

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="ABC School Meal Scheduler", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.include_router(run_router)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/bootstrap")
def bootstrap():
    return default_configuration()


@app.post("/api/evaluate")
def evaluate(request: EvaluateRequest):
    try:
        return MealProblem(request.catalog, request.planning).evaluate(request.schedule)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Raw nonstandard JSON can contain NaN/Infinity. Do not echo those values in
    # JSON errors, and keep exception objects in model-validator contexts private.
    detail = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})
