from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
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
