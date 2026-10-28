"""
Vercel Serverless Function: GET /api/scan
Runs parallel institutional scan across top pairs and returns Action Points.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data_feed import MARKET_SPECS, fetch_live_candles
from engine.state_machine import GodsEyeEngine

def _scan_single(sym: str, spec: dict):
    bars = fetch_live_candles(sym, granularity=300, count=60)
    partner_bars = None
    if spec.get("partner"):
        partner_bars = fetch_live_candles(spec["partner"], granularity=300, count=60)
    engine = GodsEyeEngine(symbol=sym, decimals=spec["decimals"], partner_symbol=spec.get("partner", ""))
    return asdict(engine.analyze(bars, partner_bars))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        results = []
        active_smt = None

        scan_targets = [(sym, spec) for sym, spec in MARKET_SPECS.items() if sym != "XAGUSD"]
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(_scan_single, sym, spec) for sym, spec in scan_targets]
            for f in futures:
                try:
                    ap_dict = f.result(timeout=4.0)
                    if ap_dict.get("smt_divergence") and not active_smt:
                        active_smt = ap_dict.get("smt_details")
                    results.append(ap_dict)
                except Exception:
                    pass

        results.sort(key=lambda x: (x["grade"] == "A+ EXPLOSIVE", x["grade"] == "A HIGH PROBABILITY", x["confidence_pct"]), reverse=True)

        payload = json.dumps({
            "ok": True,
            "active_smt_banner": active_smt,
            "action_points": results
        }, indent=2).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)
