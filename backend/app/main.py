"""FastAPI entry point for the MarineGuard AI backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.earth_engine_routes import router as earth_engine_router
from backend.app.prediction_routes import router as prediction_router


app = FastAPI(title="MarineGuard AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(earth_engine_router)
app.include_router(prediction_router)


@app.get("/health")
def health():
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
