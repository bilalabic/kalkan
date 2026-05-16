from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Kalkan", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
