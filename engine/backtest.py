"""
God's Eye Flux V3 - High-Fidelity Research Lab & Backtest Engine
Simulates the exact dual-tranche execution governor across live/historical candles.
Calculates net R-multiple, win rate, profit factor, max drawdown, and institutional rationale logs.
"""
from dataclasses import asdict
from typing import Any
from .state_machine import GodsEyeEngine

def run_backtest(
    bars: list[dict],
    partner_bars: list[dict] = None,
    symbol: str = "XAUUSD",
    decimals: int = 2,
    enable_smt: bool = True,
    tp1_r: float = 1.25,
    tp2_r: float = 3.50,
    be_trigger_r: float = 0.78
) -> dict[str, Any]:
    if len(bars) < 30:
        return {"error": "Not enough candle bars to run backtest."}

    engine = GodsEyeEngine(symbol=symbol, decimals=decimals)
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = [{"trade_num": 0, "cum_r": 0.0, "time": bars[25]["time"]}]

    active_trade = None
    cum_r = 0.0
    wins = 0
    losses = 0
    be_scratches = 0
    gross_profit_r = 0.0
    gross_loss_r = 0.0
    peak_r = 0.0
    max_drawdown_r = 0.0

    # Step through candle by candle to simulate real-time forward execution
    for i in range(25, len(bars)):
        window = bars[:i]
        partner_window = partner_bars[:i] if partner_bars else None
        current_bar = bars[i]

        # 1. Manage Active Trade
        if active_trade is not None:
            direction = active_trade["direction"] # 1 for Long, -1 for Short
            entry = active_trade["entry"]
            risk = active_trade["risk"]
            sl = active_trade["current_sl"]
            be_trig = active_trade["be_trigger"]
            tp1 = active_trade["tp1"]
            tp2 = active_trade["tp2"]

            high = current_bar["high"]
            low = current_bar["low"]

            # Long trade management
            if direction == 1:
                # Check BE Trigger (+0.78R)
                if not active_trade["be_activated"] and high >= be_trig:
                    active_trade["be_activated"] = True
                    active_trade["current_sl"] = entry + (0.05 * risk) # Scratch lock

                # Check TP1 (+1.25R, 70% bank)
                if not active_trade["tp1_hit"] and high >= tp1:
                    active_trade["tp1_hit"] = True
                    active_trade["banked_r"] += 0.70 * tp1_r
                    active_trade["current_sl"] = entry + (0.25 * risk) # Lock profit on runner

                # Check TP2 (+3.50R, remaining 30% runner)
                if high >= tp2:
                    active_trade["tp2_hit"] = True
                    active_trade["banked_r"] += 0.30 * tp2_r
                    trade_result_r = round(active_trade["banked_r"], 2)
                    _finalize_trade(trades, active_trade, current_bar["time"], tp2, "WIN_MACRO_DOL", trade_result_r)
                    cum_r += trade_result_r
                    wins += 1
                    gross_profit_r += trade_result_r
                    active_trade = None

                # Check Stop Loss
                elif low <= active_trade["current_sl"]:
                    exit_price = active_trade["current_sl"]
                    if active_trade["tp1_hit"]:
                        # 70% already banked at TP1, runner scratched at +0.25R
                        trade_result_r = round(active_trade["banked_r"] + (0.30 * 0.25), 2)
                        wins += 1
                        gross_profit_r += trade_result_r
                        reason = "TP1_BANKED_RUNNER_STOP"
                    elif active_trade["be_activated"]:
                        trade_result_r = 0.05
                        be_scratches += 1
                        reason = "BREAKEVEN_SCRATCH"
                    else:
                        trade_result_r = -1.0
                        losses += 1
                        gross_loss_r += 1.0
                        reason = "STOP_LOSS_HIT"

                    _finalize_trade(trades, active_trade, current_bar["time"], exit_price, reason, trade_result_r)
                    cum_r += trade_result_r
                    active_trade = None

            # Short trade management
            elif direction == -1:
                # Check BE Trigger (-0.78R)
                if not active_trade["be_activated"] and low <= be_trig:
                    active_trade["be_activated"] = True
                    active_trade["current_sl"] = entry - (0.05 * risk)

                # Check TP1 (-1.25R)
                if not active_trade["tp1_hit"] and low <= tp1:
                    active_trade["tp1_hit"] = True
                    active_trade["banked_r"] += 0.70 * tp1_r
                    active_trade["current_sl"] = entry - (0.25 * risk)

                # Check TP2 (-3.50R)
                if low <= tp2:
                    active_trade["tp2_hit"] = True
                    active_trade["banked_r"] += 0.30 * tp2_r
                    trade_result_r = round(active_trade["banked_r"], 2)
                    _finalize_trade(trades, active_trade, current_bar["time"], tp2, "WIN_MACRO_DOL", trade_result_r)
                    cum_r += trade_result_r
                    wins += 1
                    gross_profit_r += trade_result_r
                    active_trade = None

                # Check Stop Loss
                elif high >= active_trade["current_sl"]:
                    exit_price = active_trade["current_sl"]
                    if active_trade["tp1_hit"]:
                        trade_result_r = round(active_trade["banked_r"] + (0.30 * 0.25), 2)
                        wins += 1
                        gross_profit_r += trade_result_r
                        reason = "TP1_BANKED_RUNNER_STOP"
                    elif active_trade["be_activated"]:
                        trade_result_r = 0.05
                        be_scratches += 1
                        reason = "BREAKEVEN_SCRATCH"
                    else:
                        trade_result_r = -1.0
                        losses += 1
                        gross_loss_r += 1.0
                        reason = "STOP_LOSS_HIT"

                    _finalize_trade(trades, active_trade, current_bar["time"], exit_price, reason, trade_result_r)
                    cum_r += trade_result_r
                    active_trade = None

            # Update drawdown & curve
            if active_trade is None:
                peak_r = max(peak_r, cum_r)
                drawdown = peak_r - cum_r
                max_drawdown_r = max(max_drawdown_r, drawdown)
                equity_curve.append({
                    "trade_num": len(trades),
                    "cum_r": round(cum_r, 2),
                    "time": current_bar["time"]
                })

        # 2. Check for New Setup if Idle
        if active_trade is None and i < len(bars) - 5:
            ap = engine.analyze(window, partner_window)
            if ap.action in ["BUY / LONG", "SELL / SHORT"]:
                if enable_smt and not ap.smt_divergence and ap.grade != "A+ EXPLOSIVE":
                    pass # Skip if strict SMT filter is active
                else:
                    active_trade = {
                        "id": f"TRD_{len(trades)+1:03d}",
                        "symbol": symbol,
                        "action": ap.action,
                        "direction": 1 if "BUY" in ap.action else -1,
                        "entry_time": current_bar["time"],
                        "entry": ap.entry,
                        "initial_sl": ap.stop_loss,
                        "current_sl": ap.stop_loss,
                        "risk": ap.risk_r,
                        "be_trigger": ap.be_trigger,
                        "tp1": ap.tp1,
                        "tp2": ap.tp2,
                        "archetype": ap.archetype,
                        "why_action": ap.why_action,
                        "why_entry": ap.why_entry,
                        "be_activated": False,
                        "tp1_hit": False,
                        "tp2_hit": False,
                        "banked_r": 0.0
                    }

    total_completed = len(trades)
    win_rate = round((wins / total_completed * 100), 1) if total_completed > 0 else 0.0
    profit_factor = round(gross_profit_r / gross_loss_r, 2) if gross_loss_r > 0 else (round(gross_profit_r, 2) if gross_profit_r > 0 else 1.0)

    return {
        "summary": {
            "symbol": symbol,
            "total_trades": total_completed,
            "wins": wins,
            "losses": losses,
            "be_scratches": be_scratches,
            "win_rate_pct": win_rate,
            "net_r": round(cum_r, 2),
            "profit_factor": profit_factor,
            "max_drawdown_r": round(max_drawdown_r, 2),
            "tp1_config": f"+{tp1_r}R (70% Bank)",
            "tp2_config": f"+{tp2_r}R (30% DOL)",
            "smt_filter_active": enable_smt
        },
        "equity_curve": equity_curve,
        "trades": trades[-50:] # Return last 50 trades with full rationales
    }

def _finalize_trade(trades_list: list, trade: dict, exit_time: int, exit_price: float, outcome: str, net_r: float):
    trades_list.append({
        "id": trade["id"],
        "symbol": trade["symbol"],
        "action": trade["action"],
        "archetype": trade["archetype"],
        "entry_time": trade["entry_time"],
        "exit_time": exit_time,
        "entry": trade["entry"],
        "exit": exit_price,
        "initial_sl": trade["initial_sl"],
        "tp1": trade["tp1"],
        "tp2": trade["tp2"],
        "net_r": net_r,
        "outcome": outcome,
        "why_action": trade["why_action"],
        "why_entry": trade["why_entry"]
    })
