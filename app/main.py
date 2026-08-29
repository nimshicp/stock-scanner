from fastapi import FastAPI
from app.config.settings import settings

app = FastAPI(title="Stock Breakout Scanner")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Stock Breakout Scanner is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
