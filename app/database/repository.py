import sqlite3
import datetime
import os
from typing import List, Optional

DB_PATH = "data/scanner.db"

def init_db():
    """Creates the necessary tables if they don't exist."""
    if not os.path.exists("data"):
        os.makedirs("data")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for tracked symbols
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            is_active INTEGER DEFAULT 1,
            previous_ltp REAL DEFAULT 0.0
        )
    ''')
    
    # Migrate old DB if it doesn't have is_active or previous_ltp
    cursor.execute("PRAGMA table_info(watchlist)")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_active" not in columns:
        cursor.execute("ALTER TABLE watchlist ADD COLUMN is_active INTEGER DEFAULT 1")
    if "previous_ltp" not in columns:
        cursor.execute("ALTER TABLE watchlist ADD COLUMN previous_ltp REAL DEFAULT 0.0")
    
    # Table for cached historical highs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_highs (
            symbol TEXT PRIMARY KEY,
            highest_price REAL,
            last_calculated_date TEXT
        )
    ''')
    
    # Table for alerts log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            alert_date TEXT,
            breakout_price REAL
        )
    ''')

    # Table for secure server-side FYERS authentication token storage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fyers_tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT,
            refresh_token TEXT,
            access_token_expires_at REAL,
            refresh_token_expires_at REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def add_symbol_to_watchlist(symbol: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO watchlist (symbol, is_active, previous_ltp) 
            VALUES (?, 1, 0.0) 
            ON CONFLICT(symbol) DO UPDATE SET is_active=1
        """, (symbol,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error adding symbol: {e}")
        return False

def bulk_add_symbols(symbols: List[str]) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Soft delete symbols not in the new universe
        placeholders = ','.join(['?'] * len(symbols))
        cursor.execute(f"UPDATE watchlist SET is_active=0 WHERE symbol NOT IN ({placeholders})", symbols)
        
        # Insert or reactivate symbols
        data = [(sym,) for sym in symbols]
        cursor.executemany("""
            INSERT INTO watchlist (symbol, is_active, previous_ltp) 
            VALUES (?, 1, 0.0) 
            ON CONFLICT(symbol) DO UPDATE SET is_active=1
        """, data)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error during bulk add: {e}")
        return False

def deactivate_symbol(symbol: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE watchlist SET is_active=0 WHERE symbol=?", (symbol,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error deactivating symbol: {e}")
        return False

def get_watchlist() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE is_active=1")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_watchlist_with_ltp() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, previous_ltp FROM watchlist WHERE is_active=1")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def update_previous_ltp(symbol: str, ltp: float) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE watchlist SET previous_ltp=? WHERE symbol=?", (ltp, symbol))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error updating previous_ltp: {e}")
        return False

def get_historical_high(symbol: str) -> Optional[float]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT highest_price FROM historical_highs WHERE symbol=?", (symbol,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_historical_high(symbol: str, highest_price: float):
    today_str = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO historical_highs (symbol, highest_price, last_calculated_date)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET 
            highest_price=excluded.highest_price,
            last_calculated_date=excluded.last_calculated_date
    """, (symbol, highest_price, today_str))
    conn.commit()
    conn.close()

def log_alert(symbol: str, price: float) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today_date = datetime.date.today().isoformat()
        cursor.execute("INSERT INTO alerts_log (symbol, alert_date, breakout_price) VALUES (?, ?, ?)", 
                       (symbol, today_date, price))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error logging alert: {e}")
        return False

def save_fyers_tokens(access_token: str, refresh_token: str, access_expiry: float, refresh_expiry: float) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fyers_tokens (id, access_token, refresh_token, access_token_expires_at, refresh_token_expires_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                access_token=excluded.access_token,
                refresh_token=excluded.refresh_token,
                access_token_expires_at=excluded.access_token_expires_at,
                refresh_token_expires_at=excluded.refresh_token_expires_at
        """, (access_token, refresh_token, access_expiry, refresh_expiry))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error saving fyers tokens: {e}")
        return False

def get_fyers_tokens() -> dict | None:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT access_token, refresh_token, access_token_expires_at, refresh_token_expires_at FROM fyers_tokens WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "access_token": row[0],
                "refresh_token": row[1],
                "access_token_expires_at": row[2],
                "refresh_token_expires_at": row[3]
            }
        return None
    except Exception as e:
        print(f"DB Error retrieving fyers tokens: {e}")
        return None
