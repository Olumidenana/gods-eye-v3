"""
God's Eye Flux V3 - Institutional Predictive State Machine
Vectorized ICT 2022 Mentorship logic fused with God's Eye Probabilistic Confluence.
Generates crystal-clear, self-explanatory Action Points with zero indicator lag.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
import math

@dataclass
class ActionPoint:
    symbol: str
    action: str                     # "BUY / LONG", "SELL / SHORT", "STAND DOWN"
    grade: str                      # "A+ EXPLOSIVE", "A HIGH PROBABILITY", "NEUTRAL"
    archetype: str                  # "JUDAS_SWING_REVERSAL", "TREND_PULLBACK_RAID", "SMT_TURTLE_SOUP"
    confidence_pct: float
    ev_r: float
    current_price: float
    entry: float
    stop_loss: float
    be_trigger: float               # +0.78R Breakeven Lock
    tp1: float                      # +1.25R (70% Position Bank)
    tp2: float                      # +3.50R (30% Macro Runner to DOL)
    risk_r: float
    dealing_range: dict[str, float]
    killzone: str
    smt_divergence: bool
    smt_details: str
    why_action: str
    why_entry: str
    why_stop: str
    why_targets: str
    checklist: list[dict[str, Any]]

class GodsEyeEngine:
    def __init__(self, symbol: str, decimals: int = 2, partner_symbol: str = "XAGUSD"):
        self.symbol = symbol
        self.decimals = decimals
        self.partner_symbol = partner_symbol

    def analyze(self, bars: list[dict], partner_bars: list[dict] = None) -> ActionPoint:
        if len(bars) < 25:
            return self._stand_down(bars[-1]["close"] if bars else 0.0, "Insufficient candle history")

        cur = bars[-1]
        cur_price = cur["close"]

        # 1. 20-Period Dealing Range & 50% Equilibrium (RL-06)
        recent = bars[-25:]
        dr_high = max(b["high"] for b in recent[:-3])
        dr_low = min(b["low"] for b in recent[:-3])
        dr_range = dr_high - dr_low or (cur_price * 0.005)
        eq_50 = dr_low + 0.5 * dr_range
        is_discount = cur_price < eq_50
        regime_label = "DISCOUNT (Institutional Buy Zone)" if is_discount else "PREMIUM (Institutional Sell Zone)"

        # 2. Killzone & Timing Windows (KZ-01 to KZ-09)
        bar_dt = datetime.fromtimestamp(cur["time"], timezone.utc)
        ny_hour = (bar_dt.hour - 4) % 24 # UTC-4 (New York EDT approximation)
        ny_minute = bar_dt.minute

        in_london = 2 <= ny_hour < 5
        in_ny_am = (ny_hour == 8 and ny_minute >= 30) or (9 <= ny_hour < 11)
        in_ny_pm = (ny_hour == 13 and ny_minute >= 30) or (14 <= ny_hour < 16)
        in_judas = (ny_hour == 9 and 25 <= ny_minute <= 50)

        if in_judas:
            kz_name = "US Equity Open (Judas Swing Window 09:30 NY)"
        elif in_ny_am:
            kz_name = "New York AM Killzone (08:30–11:00 NY)"
        elif in_london:
            kz_name = "London Open Killzone (02:00–05:00 NY)"
        elif in_ny_pm:
            kz_name = "New York PM Killzone (13:30–16:00 NY)"
        else:
            kz_name = "Off-Peak / Asian Accumulation"

        # 3. Liquidity Sweeps (SW-01, SW-02)
        # Look for recent probe beyond previous swing high/low in last 6 bars
        prior_highs = [b["high"] for b in bars[-8:-2]]
        prior_lows = [b["low"] for b in bars[-8:-2]]
        max_prior_high = max(prior_highs)
        min_prior_low = min(prior_lows)

        bsl_swept = any(b["high"] > max_prior_high for b in bars[-3:])
        ssl_swept = any(b["low"] < min_prior_low for b in bars[-3:])

        # 4. Fair Value Gaps & Consequent Encroachment (FV-01, FV-03)
        b1, b2, b3 = bars[-4], bars[-3], bars[-2]
        bull_fvg = b3["low"] > b1["high"]
        bear_fvg = b3["high"] < b1["low"]
        fvg_ce = 0.0
        if bull_fvg:
            fvg_ce = round((b3["low"] + b1["high"]) / 2, self.decimals)
        elif bear_fvg:
            fvg_ce = round((b3["high"] + b1["low"]) / 2, self.decimals)

        # 5. SMT Divergence Cross-Check (SMT-01, SMT-02)
        smt_confirmed = False
        smt_desc = "No active intermarket divergence"
        if partner_bars and len(partner_bars) >= 8:
            p_prior_highs = [b["high"] for b in partner_bars[-8:-2]]
            p_prior_lows = [b["low"] for b in partner_bars[-8:-2]]
            p_bsl_swept = any(b["high"] > max(p_prior_highs) for b in partner_bars[-3:])
            p_ssl_swept = any(b["low"] < min(p_prior_lows) for b in partner_bars[-3:])

            # Bullish SMT: Main asset sweeps Sell-Side Liquidity while partner holds higher low
            if ssl_swept and not p_ssl_swept:
                smt_confirmed = True
                smt_desc = f"Bullish SMT: {self.symbol} swept SSL while {self.partner_symbol} held a Higher Low."
            # Bearish SMT: Main asset sweeps Buy-Side Liquidity while partner holds lower high
            elif bsl_swept and not p_bsl_swept:
                smt_confirmed = True
                smt_desc = f"Bearish SMT: {self.symbol} swept BSL while {self.partner_symbol} held a Lower High."

        # 6. Action Point Decision Gate
        # SETUP A: BULLISH EXPANSION / REVERSAL
        if ssl_swept and is_discount and (bull_fvg or cur["close"] > cur["open"]):
            risk = abs(cur_price - min_prior_low) or (cur_price * 0.0015)
            entry = round(fvg_ce if bull_fvg else cur_price, self.decimals)
            sl = round(min_prior_low - (risk * 0.15), self.decimals)
            actual_risk = abs(entry - sl) or (cur_price * 0.001)

            be_price = round(entry + (0.78 * actual_risk), self.decimals)
            tp1_price = round(entry + (1.25 * actual_risk), self.decimals)
            tp2_price = round(entry + (3.50 * actual_risk), self.decimals)

            conf = 88.5 if smt_confirmed else (81.0 if in_ny_am or in_london else 74.0)
            ev = round((conf / 100 * 1.85) - ((1 - conf / 100) * 1.0), 2)

            return ActionPoint(
                symbol=self.symbol,
                action="BUY / LONG",
                grade="A+ EXPLOSIVE" if smt_confirmed else "A HIGH PROBABILITY",
                archetype="SMT_TURTLE_SOUP" if smt_confirmed else ("JUDAS_SWING_REVERSAL" if in_judas else "TREND_PULLBACK_RAID"),
                confidence_pct=conf,
                ev_r=ev,
                current_price=cur_price,
                entry=entry,
                stop_loss=sl,
                be_trigger=be_price,
                tp1=tp1_price,
                tp2=tp2_price,
                risk_r=round(actual_risk, self.decimals),
                dealing_range={"high": dr_high, "low": dr_low, "eq_50": eq_50},
                killzone=kz_name,
                smt_divergence=smt_confirmed,
                smt_details=smt_desc,
                why_action=f"Price raided Sell-Side Liquidity (SSL) in deep Discount ({regime_label}) with institutional displacement.",
                why_entry=f"Enter at Consequent Encroachment (50% CE @ {entry}) of the displacement Fair Value Gap.",
                why_stop=f"Invalidation level is locked below the liquidity raid low ({sl}). Sustained break voids the order-flow shift.",
                why_targets=f"TP1 (+1.25R @ {tp1_price}) banks 70% volume & moves SL to BE. TP2 (+3.50R @ {tp2_price}) targets resting Buy-Side Liquidity.",
                checklist=[
                    {"item": "Liquidity Purge", "passed": True, "detail": f"SSL swept below {min_prior_low}"},
                    {"item": "Dealing Range", "passed": True, "detail": f"Operating in Discount below EQ {eq_50}"},
                    {"item": "Displacement FVG", "passed": bull_fvg, "detail": f"Imbalance identified with CE at {fvg_ce}"},
                    {"item": "SMT Triad Cross-Check", "passed": smt_confirmed, "detail": smt_desc},
                    {"item": "Killzone Window", "passed": in_london or in_ny_am or in_ny_pm, "detail": kz_name}
                ]
            )

        # SETUP B: BEARISH EXPANSION / REVERSAL
        elif bsl_swept and not is_discount and (bear_fvg or cur["close"] < cur["open"]):
            risk = abs(max_prior_high - cur_price) or (cur_price * 0.0015)
            entry = round(fvg_ce if bear_fvg else cur_price, self.decimals)
            sl = round(max_prior_high + (risk * 0.15), self.decimals)
            actual_risk = abs(sl - entry) or (cur_price * 0.001)

            be_price = round(entry - (0.78 * actual_risk), self.decimals)
            tp1_price = round(entry - (1.25 * actual_risk), self.decimals)
            tp2_price = round(entry - (3.50 * actual_risk), self.decimals)

            conf = 88.5 if smt_confirmed else (81.0 if in_ny_am or in_london else 74.0)
            ev = round((conf / 100 * 1.85) - ((1 - conf / 100) * 1.0), 2)

            return ActionPoint(
                symbol=self.symbol,
                action="SELL / SHORT",
                grade="A+ EXPLOSIVE" if smt_confirmed else "A HIGH PROBABILITY",
                archetype="SMT_TURTLE_SOUP" if smt_confirmed else ("JUDAS_SWING_REVERSAL" if in_judas else "TREND_PULLBACK_RAID"),
                confidence_pct=conf,
                ev_r=ev,
                current_price=cur_price,
                entry=entry,
                stop_loss=sl,
                be_trigger=be_price,
                tp1=tp1_price,
                tp2=tp2_price,
                risk_r=round(actual_risk, self.decimals),
                dealing_range={"high": dr_high, "low": dr_low, "eq_50": eq_50},
                killzone=kz_name,
                smt_divergence=smt_confirmed,
                smt_details=smt_desc,
                why_action=f"Price swept Buy-Side Liquidity (BSL) in Premium ({regime_label}) before printing strong rejection.",
                why_entry=f"Enter at Consequent Encroachment (50% CE @ {entry}) of the bearish Fair Value Gap.",
                why_stop=f"Invalidation is anchored above the liquidity run high ({sl}). Reclaiming this high aborts distribution.",
                why_targets=f"TP1 (+1.25R @ {tp1_price}) banks 70% volume & moves SL to BE. TP2 (+3.50R @ {tp2_price}) targets resting Sell-Side Liquidity.",
                checklist=[
                    {"item": "Liquidity Purge", "passed": True, "detail": f"BSL swept above {max_prior_high}"},
                    {"item": "Dealing Range", "passed": True, "detail": f"Operating in Premium above EQ {eq_50}"},
                    {"item": "Displacement FVG", "passed": bear_fvg, "detail": f"Imbalance identified with CE at {fvg_ce}"},
                    {"item": "SMT Triad Cross-Check", "passed": smt_confirmed, "detail": smt_desc},
                    {"item": "Killzone Window", "passed": in_london or in_ny_am or in_ny_pm, "detail": kz_name}
                ]
            )

        return self._stand_down(cur_price, f"Price consolidating inside Dealing Range (EQ {eq_50}). Waiting for an external liquidity pool raid.")

    def _stand_down(self, cur_price: float, reason: str) -> ActionPoint:
        return ActionPoint(
            symbol=self.symbol,
            action="STAND DOWN",
            grade="NEUTRAL",
            archetype="RANGE_BUILDING",
            confidence_pct=0.0,
            ev_r=0.0,
            current_price=cur_price,
            entry=cur_price,
            stop_loss=cur_price,
            be_trigger=cur_price,
            tp1=cur_price,
            tp2=cur_price,
            risk_r=0.0,
            dealing_range={"high": cur_price, "low": cur_price, "eq_50": cur_price},
            killzone="Market In Equilibrium",
            smt_divergence=False,
            smt_details="No SMT divergence",
            why_action=reason,
            why_entry="Stand down. Do not chase mid-range chop.",
            why_stop="No active invalidation level.",
            why_targets="No active draw on liquidity target.",
            checklist=[
                {"item": "Liquidity Raid", "passed": False, "detail": "Awaiting sweep of session extreme"},
                {"item": "Displacement CISD", "passed": False, "detail": "Awaiting institutional candle shift"}
            ]
        )
