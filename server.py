"""
God's Eye Flux V3 - High-Velocity Local Server
Zero external setup. Pure Python. Serves the Streamlined Action-Point UI and Research Lab.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

from engine.data_feed import MARKET_SPECS, fetch_live_candles
from engine.state_machine import GodsEyeEngine
from engine.backtest import run_backtest

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

def _scan_single(sym: str, spec: dict):
    bars = fetch_live_candles(sym, granularity=300, count=60)
    partner_bars = None
    if spec.get("partner"):
        partner_bars = fetch_live_candles(spec["partner"], granularity=300, count=60)
    engine = GodsEyeEngine(symbol=sym, decimals=spec["decimals"], partner_symbol=spec.get("partner", ""))
    return asdict(engine.analyze(bars, partner_bars))

class GodsEyeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. LIVE ACTION-POINT SCANNER
        if path == "/api/scan":
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
                    except Exception as e:
                        pass

            # Sort: A+ and A setups first
            results.sort(key=lambda x: (x["grade"] == "A+ EXPLOSIVE", x["grade"] == "A HIGH PROBABILITY", x["confidence_pct"]), reverse=True)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "active_smt_banner": active_smt,
                "action_points": results
            }, indent=2).encode())
            return

        # 2. CANDLE DATA FOR CHARTING
        elif path == "/api/candles":
            sym = query.get("symbol", ["XAUUSD"])[0]
            count = int(query.get("count", ["120"])[0])
            bars = fetch_live_candles(sym, granularity=300, count=count)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "symbol": sym, "candles": bars}).encode())
            return

        # 3. RESEARCH LAB BACKTEST ENGINE
        elif path == "/api/backtest":
            sym = query.get("symbol", ["XAUUSD"])[0]
            enable_smt = query.get("enable_smt", ["1"])[0] == "1"
            tp1_r = float(query.get("tp1", ["1.25"])[0])
            tp2_r = float(query.get("tp2", ["3.50"])[0])
            count = int(query.get("count", ["350"])[0])

            spec = MARKET_SPECS.get(sym, MARKET_SPECS["XAUUSD"])
            bars = fetch_live_candles(sym, granularity=300, count=count)
            partner_bars = None
            if spec.get("partner"):
                partner_bars = fetch_live_candles(spec["partner"], granularity=300, count=count)

            report = run_backtest(
                bars=bars,
                partner_bars=partner_bars,
                symbol=sym,
                decimals=spec["decimals"],
                enable_smt=enable_smt,
                tp1_r=tp1_r,
                tp2_r=tp2_r
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "report": report}, indent=2).encode())
            return

        return super().do_GET()

def start_server(port: int = 8080):
    print("=" * 64)
    print("  GOD'S EYE FLUX V3 - ACTION RADAR & RESEARCH LAB")
    print(f"  Local Terminal running at: http://localhost:{port}")
    print("  Zero external keys required. Live feeds active.")
    print("=" * 64)
    server = HTTPServer(("0.0.0.0", port), GodsEyeHandler)
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_server(port)
