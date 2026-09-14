import datetime
from app.fyers.auth import get_fyers_model
from app.database import repository

def sync_holdings_with_db():
    """
    Fetches actual Fyers holdings and updates the SQLite watchlist.
    Adds new stocks, removes sold stocks.
    """
    print(f"[{datetime.datetime.now()}] Syncing Fyers holdings with database...")
    try:
        fyers = get_fyers_model()
        response = fyers.holdings()
        
        if response.get("s") != "ok":
            print(f"Failed to fetch holdings: {response}")
            return
            
        holdings_data = response.get("holdings", [])
        
        # Extract the symbol strings from the holdings
        current_holdings = set([item.get("symbol") for item in holdings_data if item.get("symbol")])
        
        # Get what we currently have in DB
        db_watchlist = set(repository.get_watchlist())
        
        # Find new stocks to add
        new_stocks = current_holdings - db_watchlist
        for symbol in new_stocks:
            print(f"New stock found in holdings: {symbol}. Adding to DB...")
            repository.add_symbol_to_watchlist(symbol)
            
        # Find sold stocks to remove
        sold_stocks = db_watchlist - current_holdings
        for symbol in sold_stocks:
            print(f"Stock missing from holdings: {symbol}. Deactivating in DB...")
            repository.deactivate_symbol(symbol)
            
        print(f"Sync complete. Added {len(new_stocks)}, Removed {len(sold_stocks)}.")
        
    except Exception as e:
        print(f"Error syncing holdings: {e}")
