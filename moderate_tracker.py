import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ==========================================
# 1. CONFIGURATION (HARDCODED FOR THIS TEST)
# ==========================================
# REPLACE THE TEXT BELOW WITH YOUR ACTUAL TOKEN AND CHAT ID
# Keep the quotation marks!
TELEGRAM_TOKEN = "8700031510:AAGEpKDMzEfvI0W9W3w2EaCV2dSJS2A9JHs"
TELEGRAM_CHAT_ID = "5340720353"

RISK_FREE_RATE = 0.060 

ASSETS = {
    "LQ45 (Equity)": "^JKLQ45",
    "Gold (Hedge)": "GC=F",
    "USD/IDR (Valas)": "USDIDR=X"
}

# ==========================================
# 2. DATA & METRICS ENGINE
# ==========================================
def fetch_and_calculate():
    results = []
    today = datetime.now().strftime("%d %b %Y")
    
    for asset_name, ticker in ASSETS.items():
        try:
            data = yf.download(ticker, period="2y", progress=False)
            if data.empty: continue
            
            if isinstance(data.columns, pd.MultiIndex):
                prices = data.xs('Close', level=0, axis=1).iloc[:, 0]
            else:
                prices = data['Close']

            total_return = (prices.iloc[-1] / prices.iloc[0]) - 1
            ann_return = (1 + total_return) ** (1 / 2.0) - 1
            
            daily_returns = prices.pct_change().dropna()
            ann_volatility = daily_returns.std() * np.sqrt(252)
            sharpe = (ann_return - RISK_FREE_RATE) / ann_volatility if ann_volatility != 0 else 0
            
            rolling_max = prices.cummax()
            drawdown = (prices / rolling_max) - 1
            max_dd = drawdown.min()
            
            asset_type = "EQUITY" if "Equity" in asset_name else "HEDGE"
            
            results.append({
                "name": asset_name, "price": prices.iloc[-1],
                "ann_return": ann_return, "sharpe": sharpe,
                "max_dd": max_dd, "type": asset_type
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            
    return results, today

def score_asset(asset):
    score = 5
    if asset["type"] == "EQUITY":
        if asset["ann_return"] >= 0.08: score += 2
        if asset["sharpe"] >= 0.8: score += 2
        if asset["max_dd"] >= -0.15: score += 1
    else:
        if asset["sharpe"] >= 0.5: score += 2
        if asset["max_dd"] >= -0.10: score += 2
    return min(score, 10)

# ==========================================
# 3. TELEGRAM INTEGRATION
# ==========================================
def send_telegram_message(results, today):
    # This will print a safe preview of your token to prove it loaded
    print(f"🔑 Token loaded, ending in: ...{TELEGRAM_TOKEN[-5:]}")
    
    message = f"<b>📊 Daily Moderate Brief ({today})</b>\n\n"
    message += f"<i>Benchmark: SBN Ritel ~6.0% (Risk-Free)</i>\n\n"
    
    for asset in results:
        score = score_asset(asset)
        status = "✅ HOLD" if score >= 7 else "⚠️ REVIEW" if score >= 5 else "❌ AVOID"
        emoji = "🟢" if asset["ann_return"] > 0 else "🔴"
        
        message += f"<b>{emoji} {asset['name']}</b>\n"
        message += f"├ Price: {asset['price']:,.2f}\n"
        message += f"├ Ann. Return: {asset['ann_return']:.2%}\n"
        message += f"├ Sharpe Ratio: {asset['sharpe']:.2f}\n"
        message += f"├ Max Drawdown: {asset['max_dd']:.2%}\n"
        message += f"└ Moderate Score: <b>{score}/10</b> | Status: <b>{status}</b>\n\n"

    message += "<i>💡 Tip: Score 7+ means the asset aligns with moderate risk criteria.</i>"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Successfully sent to Telegram!")
        else:
            print(f"❌ Telegram API Error: {response.text}")
    except Exception as e:
        print(f"❌ Network Error: {e}")

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting IndoModerate Tracker...")
    results, today = fetch_and_calculate()
    if results:
        send_telegram_message(results, today)