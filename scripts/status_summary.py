import urllib.request
import json

try:
    resp = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/futures/state")
    data = json.loads(resp.read().decode())
    print("=== LIVE FUTURES DASHBOARD STATE ===")
    print("Bot Status:", data.get("bot", {}).get("status"))
    print("Timeframe:", data.get("bot", {}).get("timeframe"))
    print("Leverage:", data.get("bot", {}).get("leverage"))
    print("Margin USD:", data.get("bot", {}).get("marginUsd"))
    print("Balance:", data.get("account", {}).get("balance"))
    print("Available Balance:", data.get("account", {}).get("availableBalance"))
    print("Max Daily Loss:", data.get("risk", {}).get("maxDailyLoss"))
    print("Session Target:", data.get("risk", {}).get("sessionProfitTarget"))
    print("Trades Count:", data.get("risk", {}).get("tradesCount"))
    print("Signal Matrix:", data.get("signal", {}).get("reason"), "|", data.get("signal", {}).get("rejection_reason"))
except Exception as e:
    print("Error fetching state:", e)
