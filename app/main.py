from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel

from app.config.settings import settings
from app.fyers.auth import get_auth_url, generate_access_token
from app.fyers.token_manager import get_fyers_model_dynamic
from app.fyers.history import get_5_year_high
from app.scanner.engine import run_master_job, run_scan
from app.database import repository

scheduler = BackgroundScheduler()

class WatchlistRequest(BaseModel):
    symbol: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and tables
    repository.init_db()
    
    # Setup scheduler for Indian Market Hours (Mon-Fri)
    # Scans exactly every 2 hours: 09:30, 11:30, 13:30, and exactly at equity close 15:30
    scheduler.add_job(run_master_job, 'cron', day_of_week='mon-fri', hour='9,11,13,15', minute=30)
    scheduler.start()
    yield
    # Shutdown scheduler on exit
    scheduler.shutdown()

app = FastAPI(title="Stock Breakout Scanner", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Stock Breakout Scanner is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/auth/login")
def login_to_fyers():
    """Generates the FYERS login URL and redirects the user to it."""
    url = get_auth_url()
    return RedirectResponse(url)

@app.get("/callback")
def fyers_callback(request: Request):
    """Callback route for FYERS authentication."""
    auth_code = request.query_params.get("auth_code")
    
    if not auth_code:
        error_msg = request.query_params.get("message", "Unknown error during authentication")
        raise HTTPException(status_code=400, detail=f"Missing auth_code in callback: {error_msg}")
    
    try:
        # Exchanges auth code and securely stores access + refresh tokens in SQLite
        generate_access_token(auth_code)
        
        return {
            "status": "success", 
            "message": "Successfully authenticated with FYERS! Tokens securely stored.",
            "next_step": "Go to http://localhost:8000/api/auth/profile to test your connection."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/api/auth/profile")
def get_profile():
    """Fetches the user's FYERS profile to test the API connection."""
    try:
        fyers = get_fyers_model_dynamic()
        response = fyers.get_profile()
        return response
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/scanner/history/{symbol}")
def test_history(symbol: str):
    """Test route to fetch the 5-year high for a given symbol."""
    try:
        fyers = get_fyers_model_dynamic()
        high = get_5_year_high(fyers, symbol)
        return {
            "symbol": symbol,
            "5_year_high": high,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scanner/run")
def run_scan_now():
    """Manually trigger the scheduled scan for testing."""
    run_scan()
    return {"status": "success", "message": "Scan completed. Check your terminal logs and Telegram."}

@app.post("/api/watchlist")
def add_watchlist(request: WatchlistRequest):
    """Add a symbol to the database watchlist."""
    success = repository.add_symbol_to_watchlist(request.symbol)
    if success:
        return {"status": "success", "message": f"Added {request.symbol} to watchlist"}
    raise HTTPException(status_code=500, detail="Failed to add symbol")

@app.get("/api/watchlist")
def get_watchlist():
    """Get all symbols currently in the watchlist."""
    symbols = repository.get_watchlist()
    return {"status": "success", "count": len(symbols), "watchlist": symbols}

@app.get("/api/alerts/test")
def test_telegram():
    """Test route to verify Telegram bot credentials."""
    from app.alerts.telegram import send_telegram_alert
    try:
        send_telegram_alert("👋 Hello from your Stock Breakout Scanner! Telegram is working perfectly!")
        return {"status": "success", "message": "Test alert sent. Check your Telegram app!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/universe/sync")
def sync_universe(background_tasks: BackgroundTasks):
    """Test route to manually trigger NIFTY 500 Universe Sync & Historical Fetch."""
    from app.stocks.universe import run_universe_setup
    try:
        # Run in background because 500 API calls will take ~15 minutes
        background_tasks.add_task(run_universe_setup)
        return {"status": "success", "message": "Universe Sync started in the background! Check terminal logs."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/database")
def view_database():
    """Quickly view the contents of the SQLite database."""
    import sqlite3
    conn = sqlite3.connect('data/scanner.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM watchlist')
    watchlist = c.fetchall()
    
    c.execute('SELECT * FROM historical_highs')
    highs = c.fetchall()
    
    c.execute('SELECT * FROM alerts_log')
    alerts = c.fetchall()
    
    return {
        "watchlist": [row[0] for row in watchlist],
        "historical_highs": [{"symbol": r[0], "high": r[1], "date_calculated": r[2]} for r in highs],
        "alerts_sent": [{"symbol": r[0], "date": r[1], "price": r[2]} for r in alerts]
    }
