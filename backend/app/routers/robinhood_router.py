"""
HELIOS Phase 16 — Robinhood FastAPI router.

Prefix : /api/robinhood
Tag    : robinhood

All order-placement endpoints require explicit human approval
(approval_confirmed=True in the request body).  A prominent warning is
included in every place-order response to reinforce this.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/robinhood", tags=["robinhood"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ReviewOrderBody(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: Optional[float] = None
    dollar_amount: Optional[float] = None
    limit_price: Optional[float] = None


class PlaceOrderBody(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: Optional[float] = None
    limit_price: Optional[float] = None
    approval_confirmed: bool = False


class WatchlistBody(BaseModel):
    symbol: str
    name: str


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


@router.get("/accounts")
def accounts():
    try:
        from market_data.robinhood import get_accounts
        return get_accounts()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/portfolio")
def portfolio():
    try:
        from market_data.robinhood import get_portfolio
        return get_portfolio()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@router.get("/positions")
def positions():
    try:
        from market_data.robinhood import get_positions
        return get_positions()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/positions/options")
def option_positions():
    try:
        from market_data.robinhood import get_option_positions
        return get_option_positions()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.get("/orders")
def orders(
    symbol: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
):
    try:
        from market_data.robinhood import get_orders
        return get_orders(symbol=symbol, state=state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/orders/{order_id}")
def order(order_id: str):
    try:
        from market_data.robinhood import get_order
        return get_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/orders/{order_id}")
def cancel_order(order_id: str):
    try:
        from market_data.robinhood import cancel_order as _cancel_order
        return _cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/orders/review")
def review_order(body: ReviewOrderBody):
    try:
        from market_data.robinhood import review_order as _review_order
        return _review_order(
            symbol=body.symbol,
            side=body.side,
            order_type=body.order_type,
            quantity=body.quantity,
            dollar_amount=body.dollar_amount,
            limit_price=body.limit_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/orders/place")
def place_order(body: PlaceOrderBody):
    """
    WARNING: This endpoint places a REAL order on Robinhood with REAL money.
    approval_confirmed must be True in the request body, confirming that a
    human has reviewed the order details before submission.
    """
    if not body.approval_confirmed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Human approval required. "
                "Set approval_confirmed=True only after a human has reviewed the order."
            ),
        )
    try:
        from market_data.robinhood import place_order as _place_order
        result = _place_order(
            symbol=body.symbol,
            side=body.side,
            order_type=body.order_type,
            quantity=body.quantity,
            limit_price=body.limit_price,
            approval_confirmed=body.approval_confirmed,
        )
        return {
            "warning": (
                "A REAL order has been submitted to Robinhood using REAL funds. "
                "Review your Robinhood account to confirm the order status."
            ),
            "order": result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Quotes & Fundamentals
# ---------------------------------------------------------------------------


@router.get("/quotes")
def quotes(symbols: str = Query(..., description="Comma-separated ticker symbols")):
    try:
        from market_data.robinhood import get_quotes
        return get_quotes(symbols.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundamentals")
def fundamentals(symbols: str = Query(..., description="Comma-separated ticker symbols")):
    try:
        from market_data.robinhood import get_fundamentals
        return get_fundamentals(symbols.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/historicals/{symbol}")
def historicals(
    symbol: str,
    interval: str = Query(default="day"),
    span: str = Query(default="year"),
):
    try:
        from market_data.robinhood import get_historicals
        return get_historicals(symbol, interval=interval, span=span)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------


@router.get("/watchlists")
def watchlists():
    try:
        from market_data.robinhood import get_watchlists
        return get_watchlists()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/watchlists/{name}")
def watchlist(name: str):
    try:
        from market_data.robinhood import get_watchlist
        return get_watchlist(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/watchlists/add")
def add_to_watchlist(body: WatchlistBody):
    try:
        from market_data.robinhood import add_to_watchlist as _add
        return _add(body.symbol, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/watchlists/remove")
def remove_from_watchlist(body: WatchlistBody):
    try:
        from market_data.robinhood import remove_from_watchlist as _remove
        return _remove(body.symbol, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


@router.get("/earnings/{symbol}")
def earnings(symbol: str):
    try:
        from market_data.robinhood import get_earnings
        return get_earnings(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search")
def search(q: str = Query(..., description="Search query for instruments")):
    try:
        from market_data.robinhood import search as _search
        return _search(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
