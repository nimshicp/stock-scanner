from fyers_apiv3 import fyersModel

def get_quotes(fyers: fyersModel.FyersModel, symbols: list[str]) -> dict:
    """
    Fetches real-time quotes for a list of symbols.
    Fyers allows a maximum of 50 symbols per request.
    """
    # Join symbols with comma as required by Fyers API
    symbols_string = ",".join(symbols)
    
    data = {
        "symbols": symbols_string
    }
    
    response = fyers.quotes(data=data)
    
    # We will return the dictionary mapping symbol to its high_price and lp (last price)
    quotes_data = {}
    
    if response.get("s") == "ok" and "d" in response:
        for item in response["d"]:
            symbol = item.get("n") # Symbol name
            val = item.get("v", {}) # Values dictionary
            
            high_price = val.get("high_price")
            last_price = val.get("lp")
            
            if symbol and high_price:
                quotes_data[symbol] = {
                    "high_price": high_price,
                    "last_price": last_price
                }
    else:
        print(f"Warning: Failed to fetch quotes for {symbols}: {response}")
        
    return quotes_data
