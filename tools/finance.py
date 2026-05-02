import yfinance as yf

def get_stock_data(stock: str) -> str:
    """Provides detailed current information about a given ticker using yfinance."""
    try:
        ticker = yf.Ticker(stock)
        info = ticker.info
        if not info:
            return f"No info found for stock ticker: {stock}"
            
        md_results = [f"### Current Data for {stock}"]
        keys_of_interest = ['currentPrice', 'previousClose', 'open', 'dayLow', 'dayHigh', 
                            'fiftyTwoWeekLow', 'fiftyTwoWeekHigh', 'volume', 'marketCap', 'trailingPE']
                            
        for key in keys_of_interest:
            if key in info:
                md_results.append(f"- **{key}**: {info[key]}")
                
        return "\n".join(md_results)
    except Exception as e:
        return f"Error fetching stock data: {e}"

def get_stock_history(stock: str, start: str, end: str, interval: str) -> str:
    """Provides detailed OHLCV data for a given ticker."""
    try:
        ticker = yf.Ticker(stock)
        df = ticker.history(start=start, end=end, interval=interval)
        if df.empty:
            return f"No historical data found for {stock} in the given date range."
            
        return df.to_markdown()
    except Exception as e:
        return f"Error fetching stock history: {e}"