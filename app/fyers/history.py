import datetime
from fyers_apiv3 import fyersModel

def get_5_year_high(fyers: fyersModel.FyersModel, symbol: str) -> float | None:
    """
    Fetches 5 years of daily historical data for a symbol and calculates the highest high price.
    Fyers limits 'D' resolution history to 365 days per request, so we loop backwards 5 times.
    """
    highest_price = None
    end_date = datetime.date.today()
    
    # Loop backwards for 5 years
    for _ in range(5):
        # Calculate start date for this 1-year chunk (max 365 days)
        start_date = end_date - datetime.timedelta(days=364)
        
        data = {
            "symbol": symbol,
            "resolution": "D",
            "date_format": "1", # yyyy-mm-dd
            "range_from": start_date.strftime("%Y-%m-%d"),
            "range_to": end_date.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }
        
        # Make the API call
        response = fyers.history(data=data)
        
        if response.get("s") == "ok" and "candles" in response:
            # candle format: [timestamp, open, high, low, close, volume]
            for candle in response["candles"]:
                high = candle[2]
                if highest_price is None or high > highest_price:
                    highest_price = high
        else:
            print(f"Warning: Failed to fetch history for {symbol} between {start_date} and {end_date}: {response}")
            
        # Move end_date backwards for the next iteration
        end_date = start_date - datetime.timedelta(days=1)
        
    return highest_price
