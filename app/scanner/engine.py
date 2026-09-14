import datetime
from app.fyers.token_manager import get_fyers_model_dynamic
from app.fyers.history import get_5_year_high
from app.fyers.quotes import get_quotes
from app.alerts.telegram import send_telegram_alert
from app.database import repository

def run_scan():
    """
    Core scanner logic to be executed on a schedule.
    Fetches the daily high and compares to the 5-year high.
    Reads symbols from the SQLite database.
    """
    # Read symbols and their previous LTP from the SQLite database
    watchlist_data = repository.get_watchlist_with_ltp()
    symbols = list(watchlist_data.keys())
    
    if not symbols:
        print(f"[{datetime.datetime.now()}] Watchlist is empty. Add stocks via POST /watchlist.")
        return

    print(f"[{datetime.datetime.now()}] Running scheduled scan for {len(symbols)} symbols...")
    
    try:
        fyers = get_fyers_model_dynamic()
    except Exception as e:
        print(f"Scanner aborted: {e}")
        return

    # 1. Fetch today's quotes in chunks of 50
    chunk_size = 50
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]
        quotes = get_quotes(fyers, chunk)
        
        # 2. Compare and alert
        for symbol, data in quotes.items():
            today_high = data.get("high_price", 0)
            last_price = data.get("last_price", 0)
            
            # 3. Get 5-year high from DB
            five_year_high = repository.get_historical_high(symbol)
            if five_year_high is None:
                # Do NOT fetch history during the 2-hour scan!
                print(f"No 5Y high cached for {symbol}. Skipping breakout check.")
                continue
            
            print(f"{symbol} -> 5Y High: {five_year_high} | Today's High: {today_high} | LTP: {last_price}")
            
            # 4. Did it break out AND increase since last scan?
            previous_ltp = watchlist_data.get(symbol, 0.0)
            
            if last_price > five_year_high and last_price > previous_ltp:
                msg = (
                    f"🚨 <b>BREAKOUT ALERT!</b> 🚨\n\n"
                    f"📈 <b>Stock:</b> {symbol}\n"
                    f"💵 <b>Current Price:</b> {last_price}\n"
                    f"🔄 <b>Previous Scan:</b> {previous_ltp}\n"
                    f"📊 <b>5-Year High:</b> {five_year_high}\n"
                    f"🕒 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                send_telegram_alert(msg)
                repository.log_alert(symbol, last_price)
                
                # Update previous LTP in database so we don't alert again unless it goes even higher
                repository.update_previous_ltp(symbol, last_price)
            elif last_price > five_year_high:
                print(f"{symbol} above 5Y high, but LTP ({last_price}) didn't beat previous scan ({previous_ltp}). No alert.")

def run_master_job():
    """
    The master scheduled job for the 2-hour loop.
    Only runs the price scan using Quotes API.
    """
    run_scan()
