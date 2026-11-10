import json
import sys

# One bounded paper position. It can be stopped out, and never re-enters.
state = "waiting"
entry_price = None
max_weight_bps = 0

for line in sys.stdin:
    msg = json.loads(line)
    kind = msg.get("type")
    if kind == "hello":
        max_weight_bps = int(msg["caps"]["max_weight_bps"])
        continue
    if kind == "done":
        break
    if kind != "batch":
        continue
    account = msg["account"]
    positions = {p["symbol"]: p for p in account["positions"]}
    bars = {bar["symbol"]: bar for bar in msg["bars"]}
    orders = []
    if "CBBTC" in bars:
        price = int(bars["CBBTC"]["c"])
        if state == "waiting":
            cash = int(account["cash_quote_units"])
            amount = min(cash // 2, int(account["equity_quote_units"]) * max_weight_bps // 10000)
            if amount >= 1000000:
                orders.append({"side": "buy", "symbol": "CBBTC",
                               "notional_quote_units": str(amount),
                               "max_slippage_bps": 100, "client_id": "open"})
                entry_price = price
                state = "buy_pending"
        elif state == "buy_pending":
            if "CBBTC" in positions:
                state = "holding"
            else:
                state = "waiting"
        elif state == "holding" and "CBBTC" in positions and price * 100 <= entry_price * 95:
            orders.append({"side": "sell", "symbol": "CBBTC",
                           "qty": positions["CBBTC"]["qty"],
                           "max_slippage_bps": 100, "client_id": "stop"})
            state = "exit_pending"
        elif state == "exit_pending":
            state = "holding" if "CBBTC" in positions else "finished"
    print(json.dumps({"type": "reply", "seq": msg["seq"], "orders": orders},
                     separators=(",", ":")), flush=True)
