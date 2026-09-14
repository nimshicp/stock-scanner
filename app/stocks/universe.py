import csv
import time
import requests
import datetime
from app.database import repository
from app.fyers.token_manager import get_fyers_model_dynamic
from app.fyers.history import get_5_year_high

NIFTY_500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

def get_nifty500_symbols() -> list[str]:
    """
    Downloads the official NIFTY 500 list from NSE and maps them to Fyers API format.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(NIFTY_500_URL, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch NIFTY 500 from NSE: {response.status_code}")
        return []
        
    lines = response.text.strip().split('\n')
    reader = csv.DictReader(lines)
    
    symbols = []
    for row in reader:
        symbol = row.get('Symbol')
        if symbol:
            # Fyers format for NSE equity is generally NSE:{SYMBOL}-EQ
            symbols.append(f"NSE:{symbol}-EQ")
            
    return symbols

def sync_nifty500_with_db():
    """
    Fetches the NIFTY 500 universe and stores it in the SQLite watchlist.
    """
    print(f"[{datetime.datetime.now()}] Starting NIFTY 500 Universe Sync...")
    
    symbols = get_nifty500_symbols()
    if not symbols:
        print("Aborting sync: Failed to retrieve NIFTY 500 symbols.")
        return
        
    print(f"Successfully fetched {len(symbols)} symbols from NSE.")
    
    success = repository.bulk_add_symbols(symbols)
    if success:
        print("Database updated with NIFTY 500 universe successfully.")
    else:
        print("Failed to update database with NIFTY 500 universe.")

def update_all_historical_highs():
    """
    Iterates over all active symbols in the watchlist and updates their 5-year historical highs.
    Includes built-in rate-limiting to prevent Fyers API bans.
    """
    print(f"[{datetime.datetime.now()}] Starting Historical Highs calculation for all stocks...")
    
    try:
        fyers = get_fyers_model_dynamic()
    except Exception as e:
        print(f"Failed to authenticate with Fyers: {e}")
        return
        
    symbols = repository.get_watchlist()
    
    for symbol in symbols:
        # Check if we already have a valid high so we don't recalculate unnecessarily every day
        # (For a true rolling trailing high, we might want to recalculate periodically. For now, we fetch if missing).
        # We will recalculate if it's missing or if it's 0.0 (the old bug).
        existing_high = repository.get_historical_high(symbol)
        
        if existing_high is not None and existing_high > 0:
            # We already have a valid high, skip for now unless forced
            continue
            
        print(f"Fetching 5-year history for {symbol}...")
        try:
            five_year_high = get_5_year_high(fyers, symbol)
            
            if five_year_high is not None and five_year_high > 0:
                repository.save_historical_high(symbol, five_year_high)
                print(f"Saved 5Y High for {symbol}: {five_year_high}")
            else:
                print(f"No valid history found for {symbol}. Skipping.")
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            
        # VERY IMPORTANT: Rate limiting. Fyers History API limit is ~200 per minute.
        # 1 symbol takes 5 requests (1 per year). 5 requests * 0.1s = 0.5s.
        # Sleep for 1.5 seconds between symbols ensures we never exceed 200 requests/minute.
        time.sleep(1.5)
        
    print(f"[{datetime.datetime.now()}] Historical Highs calculation complete.")

def run_universe_setup():
    """
    Helper function to run the full universe sync and historical calculation.
    """
    sync_nifty500_with_db()
    update_all_historical_highs()
