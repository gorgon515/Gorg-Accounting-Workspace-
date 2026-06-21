"""
HELIOS Phase 16 — Robinhood market data client.

Uses the robin_stocks library with a module-level singleton and lazy login.
Credentials are read from environment variables:
  ROBINHOOD_USERNAME   (required)
  ROBINHOOD_PASSWORD   (required)
  ROBINHOOD_MFA_CODE   (optional)
"""

import os

import robin_stocks.robinhood as r

# ---------------------------------------------------------------------------
# Singleton login state
# ---------------------------------------------------------------------------

_logged_in = False


def _ensure_logged_in() -> None:
    global _logged_in
    if _logged_in:
        return
    username = os.getenv("ROBINHOOD_USERNAME", "")
    password = os.getenv("ROBINHOOD_PASSWORD", "")
    if not username or not password:
        raise ValueError(
            "ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD env vars required"
        )
    mfa = os.getenv("ROBINHOOD_MFA_CODE")
    r.login(
        username,
        password,
        mfa_code=mfa,
        store_session=True,
        expiresIn=86400,
    )
    _logged_in = True


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


def get_accounts() -> list:
    """Return a list of Robinhood account profiles."""
    _ensure_logged_in()
    try:
        result = r.account.load_account_profile(info=None)
        if not isinstance(result, list):
            result = [result]
        return result
    except Exception as exc:
        raise ValueError(f"Failed to fetch accounts: {exc}") from exc


def get_portfolio() -> dict:
    """Return the portfolio profile."""
    _ensure_logged_in()
    try:
        return r.profiles.load_portfolio_profile(info=None)
    except Exception as exc:
        raise ValueError(f"Failed to fetch portfolio: {exc}") from exc


def get_account_details() -> dict:
    """Return the account profile details."""
    _ensure_logged_in()
    try:
        return r.profiles.load_account_profile(info=None)
    except Exception as exc:
        raise ValueError(f"Failed to fetch account details: {exc}") from exc


# ---------------------------------------------------------------------------
# Positions & Holdings
# ---------------------------------------------------------------------------


def get_positions() -> list:
    """Return open stock positions, each enriched with a 'symbol' field."""
    _ensure_logged_in()
    try:
        positions = r.account.get_open_stock_positions()
        for pos in positions:
            try:
                pos["symbol"] = r.stocks.get_name_by_url(pos["instrument"])
            except Exception:
                pos["symbol"] = None
        return positions
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to fetch positions: {exc}") from exc


def get_option_positions() -> list:
    """Return open option positions."""
    _ensure_logged_in()
    try:
        return r.account.get_open_option_positions()
    except Exception as exc:
        raise ValueError(f"Failed to fetch option positions: {exc}") from exc


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def get_orders(symbol: str = None, state: str = None) -> list:
    """Return all stock orders, optionally filtered by symbol and/or state."""
    _ensure_logged_in()
    try:
        orders = r.orders.get_all_stock_orders(info=None)
        if symbol is not None:
            orders = [o for o in orders if o.get("symbol") == symbol]
        if state is not None:
            orders = [o for o in orders if o.get("state") == state]
        return orders
    except Exception as exc:
        raise ValueError(f"Failed to fetch orders: {exc}") from exc


def get_order(order_id: str) -> dict:
    """Return details for a single stock order."""
    _ensure_logged_in()
    try:
        return r.orders.get_stock_order_info(order_id)
    except Exception as exc:
        raise ValueError(f"Failed to fetch order {order_id}: {exc}") from exc


def cancel_order(order_id: str) -> dict:
    """Cancel an open stock order."""
    _ensure_logged_in()
    try:
        return r.orders.cancel_stock_order(order_id)
    except Exception as exc:
        raise ValueError(f"Failed to cancel order {order_id}: {exc}") from exc


# ---------------------------------------------------------------------------
# Quotes & Fundamentals
# ---------------------------------------------------------------------------


def get_quotes(symbols: list[str]) -> list:
    """Return quotes for one or more ticker symbols."""
    _ensure_logged_in()
    try:
        return r.stocks.get_quotes(symbols, info=None)
    except Exception as exc:
        raise ValueError(f"Failed to fetch quotes: {exc}") from exc


def get_fundamentals(symbols: list[str]) -> list:
    """Return fundamental data for one or more ticker symbols."""
    _ensure_logged_in()
    try:
        return r.stocks.get_fundamentals(symbols, info=None)
    except Exception as exc:
        raise ValueError(f"Failed to fetch fundamentals: {exc}") from exc


def get_historicals(
    symbol: str, interval: str = "day", span: str = "year"
) -> list:
    """Return historical price data for a symbol."""
    _ensure_logged_in()
    try:
        return r.stocks.get_stock_historicals(
            symbol, interval=interval, span=span
        )
    except Exception as exc:
        raise ValueError(
            f"Failed to fetch historicals for {symbol}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------


def get_watchlists() -> list:
    """Return all watchlists."""
    _ensure_logged_in()
    try:
        return r.watchlists.get_all_watchlists()
    except Exception as exc:
        raise ValueError(f"Failed to fetch watchlists: {exc}") from exc


def get_watchlist(name: str) -> dict:
    """Return a watchlist by name."""
    _ensure_logged_in()
    try:
        return r.watchlists.get_watchlist_by_name(name)
    except Exception as exc:
        raise ValueError(f"Failed to fetch watchlist '{name}': {exc}") from exc


def add_to_watchlist(symbol: str, name: str) -> dict:
    """Add a symbol to a watchlist."""
    _ensure_logged_in()
    try:
        return r.watchlists.post_symbols_to_watchlist(symbol, name)
    except Exception as exc:
        raise ValueError(
            f"Failed to add {symbol} to watchlist '{name}': {exc}"
        ) from exc


def remove_from_watchlist(symbol: str, name: str) -> dict:
    """Remove a symbol from a watchlist."""
    _ensure_logged_in()
    try:
        return r.watchlists.delete_symbols_from_watchlist(symbol, name)
    except Exception as exc:
        raise ValueError(
            f"Failed to remove {symbol} from watchlist '{name}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


def get_earnings(symbol: str) -> list:
    """Return earnings data for a symbol."""
    _ensure_logged_in()
    try:
        return r.stocks.get_earnings(symbol)
    except Exception as exc:
        raise ValueError(
            f"Failed to fetch earnings for {symbol}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Orders — REQUIRE HUMAN APPROVAL
# ---------------------------------------------------------------------------


def review_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float = None,
    dollar_amount: float = None,
    limit_price: float = None,
) -> dict:
    """
    Validate order parameters and return a preview dict.

    No order is placed. The returned dict has status='pending_approval' and
    requires_confirmation=True to make clear that human approval is required
    before calling place_order().
    """
    _ensure_logged_in()

    side = side.lower()
    order_type = order_type.lower()

    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side '{side}'. Must be 'buy' or 'sell'.")
    if order_type not in ("market", "limit"):
        raise ValueError(
            f"Invalid order_type '{order_type}'. Must be 'market' or 'limit'."
        )
    if order_type == "limit" and limit_price is None:
        raise ValueError("limit_price is required for limit orders.")
    if quantity is None and dollar_amount is None:
        raise ValueError("Either quantity or dollar_amount must be provided.")

    estimated_total: float | None = None
    if quantity is not None and limit_price is not None:
        estimated_total = round(quantity * limit_price, 2)

    return {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "dollar_amount": dollar_amount,
        "limit_price": limit_price,
        "estimated_total": estimated_total,
        "status": "pending_approval",
        "requires_confirmation": True,
    }


def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float = None,
    limit_price: float = None,
    approval_confirmed: bool = False,
) -> dict:
    """
    Place a stock order.

    approval_confirmed MUST be True — this ensures a human has explicitly
    reviewed the order before it is submitted to Robinhood.
    """
    if not approval_confirmed:
        raise ValueError(
            "Human approval required. Set approval_confirmed=True after user review."
        )

    _ensure_logged_in()

    side = side.lower()
    order_type = order_type.lower()

    try:
        if side == "buy" and order_type == "market":
            result = r.orders.order_buy_market(symbol, quantity)
        elif side == "buy" and order_type == "limit":
            result = r.orders.order_buy_limit(symbol, quantity, limit_price)
        elif side == "sell" and order_type == "market":
            result = r.orders.order_sell_market(symbol, quantity)
        elif side == "sell" and order_type == "limit":
            result = r.orders.order_sell_limit(symbol, quantity, limit_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        return result
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to place order: {exc}") from exc


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(query: str) -> list:
    """Search for instruments matching query."""
    _ensure_logged_in()
    try:
        return r.stocks.find_instrument_data(query)
    except Exception as exc:
        raise ValueError(f"Search failed for '{query}': {exc}") from exc
