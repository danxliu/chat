from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, AssetStatus, AssetClass
from config import settings

def _get_trading_client():
    """Initializes the Alpaca TradingClient using configuration settings."""
    endpoint = settings.alpaca_endpoint
    if endpoint and endpoint.endswith("/v2"):
        endpoint = endpoint[:-3]
    elif endpoint and endpoint.endswith("/v2/"):
        endpoint = endpoint[:-4]
        
    return TradingClient(
        api_key=settings.alpaca_key,
        secret_key=settings.alpaca_secret,
        paper=True,
        url_override=endpoint if endpoint else None
    )

def get_account_info() -> str:
    """Returns the trading account details like cash, buying power, and equity."""
    try:
        client = _get_trading_client()
        account = client.get_account()
        return (
            f"Account ID: {account.id}\n"
            f"Cash: {account.cash}\n"
            f"Buying Power: {account.buying_power}\n"
            f"Equity: {account.equity}\n"
            f"Status: {account.status}"
        )
    except Exception as e:
        return f"Error fetching account info: {e}"

def get_positions() -> str:
    """Returns a list of all current open trading positions."""
    try:
        client = _get_trading_client()
        positions = client.get_all_positions()
        if not positions:
            return "No open positions."
        
        result = ["### Open Positions:"]
        for p in positions:
            result.append(f"- {p.symbol}: {p.qty} shares @ {p.avg_entry_price} (Current Price: {p.current_price})")
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching positions: {e}"

def get_tickers(status: str = "active", asset_class: str = "us_equity", limit: int = 100, search: str = None) -> str:
    """
    Returns a list of available tickers/symbols from Alpaca.
    
    Args:
        status: 'active' or 'inactive'.
        asset_class: 'us_equity' or 'crypto'.
        limit: Maximum number of symbols to return (default 100).
        search: Optional string to filter symbols (case-insensitive).
    """
    try:
        client = _get_trading_client()
        
        status_enum = AssetStatus.ACTIVE if status.lower() == "active" else AssetStatus.INACTIVE
        asset_class_enum = AssetClass.US_EQUITY if asset_class.lower() == "us_equity" else AssetClass.CRYPTO
        
        search_params = GetAssetsRequest(status=status_enum, asset_class=asset_class_enum)
        assets = client.get_all_assets(search_params)
        
        # Filter tradable assets
        tradable_assets = [asset for asset in assets if asset.tradable]
        
        if search:
            search_query = search.upper()
            tradable_assets = [asset for asset in tradable_assets if search_query in asset.symbol]
            
        total_count = len(tradable_assets)
        symbols = [asset.symbol for asset in tradable_assets[:limit]]
        
        result = f"Found {total_count} tradable {asset_class} symbols (status: {status})."
        if search:
            result += f" Filtered by search: '{search}'."
            
        if symbols:
            result += f"\nSymbols (showing first {len(symbols)}):\n" + ", ".join(symbols)
        else:
            result += "\nNo matching symbols found."
            
        return result
    except Exception as e:
        return f"Error fetching tickers: {e}"

def place_order(symbol: str, qty: float, side: str, order_type: str = "market", time_in_force: str = "gtc", limit_price: float = None) -> str:
    """
    Places a trading order.
    
    Args:
        symbol: The ticker symbol (e.g., 'AAPL').
        qty: The number of shares.
        side: 'buy' or 'sell'.
        order_type: 'market' or 'limit'.
        time_in_force: 'gtc', 'day', etc.
        limit_price: Required if order_type is 'limit'.
    """
    try:
        client = _get_trading_client()
        
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        type_enum = OrderType.MARKET if order_type.lower() == "market" else OrderType.LIMIT
        
        tif_map = {
            "gtc": TimeInForce.GTC,
            "day": TimeInForce.DAY,
            "opg": TimeInForce.OPG,
            "cls": TimeInForce.CLS,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK
        }
        tif_enum = tif_map.get(time_in_force.lower(), TimeInForce.GTC)
        
        if type_enum == OrderType.MARKET:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif_enum
            )
        else:
            if limit_price is None:
                return "Error: limit_price is required for limit orders."
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif_enum,
                limit_price=limit_price
            )
            
        order = client.submit_order(order_request)
        return f"Successfully placed {side} {order_type} order for {qty} shares of {symbol}. Order ID: {order.id}"
    except Exception as e:
        return f"Error placing order: {e}"
