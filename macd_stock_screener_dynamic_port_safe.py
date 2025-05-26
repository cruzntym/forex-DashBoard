import subprocess
import sys
import importlib
import datetime
import smtplib
from email.mime.text import MIMEText
from threading import Thread
import time
import http.server
import socketserver
import threading
import io
import logging
import base64
import matplotlib.pyplot as plt
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Auto-install required packages
def auto_install(package):
    try:
        return importlib.import_module(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return importlib.import_module(package)

bt = auto_install("backtrader")
yf = auto_install("yfinance")
pd = auto_install("pandas")

# Email alert utility
def send_email(subject, body):
    sender = "iyceeu@gmail.com"
    recipient = "iyceeu@gmail.com"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, "iyceeu@gmail.com")
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

# Trading time window
def within_trading_hours():
    now = datetime.datetime.now().time()
    return datetime.time(9, 30) <= now <= datetime.time(11, 0)

# Fetch data for a stock
def fetch_live_data(symbol):
    logging.info(f"Fetching live data for {symbol}")
    return yf.download(symbol, period="5d", interval="1h")

# Screen stocks by price range, volatility and volume
def screen_stocks_by_price_range(min_price, max_price):
    sample_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'F', 'GE', 'SIRI', 'NOK', 'AMD',
        'INTC', 'X', 'T', 'PFE', 'BAC', 'NIO', 'PLTR', 'FCEL', 'UAL', 'AAL',
        'SOFI', 'C', 'KO', 'WMT', 'NVDA', 'PYPL', 'CSCO', 'CRM', 'ABNB', 'SNAP'
    ]
    candidates = []
    for symbol in sample_tickers:
        try:
            df = yf.download(symbol, period="5d", interval="1d")
            if df.empty or 'Close' not in df.columns or df['Close'].isna().any():
                continue
            if df['Close'].shape[0] < 2:
                continue
            first_price = df['Close'].iloc[0]
            last_price = df['Close'].iloc[-1]
            if pd.isna(first_price) or pd.isna(last_price):
                continue
            volatility = df['Close'].pct_change().std()
            avg_volume = df['Volume'].mean()
            if pd.isna(first_price) or pd.isna(last_price):
                continue
            direction = "Bullish" if float(last_price) > float(first_price) else "Bearish"
            if pd.notna(last_price) and min_price <= last_price < max_price and pd.notna(volatility) and pd.notna(avg_volume):
                if volatility > 0.005 and avg_volume > 500000:
                    candidates.append((symbol, volatility, avg_volume, direction))
        except Exception as e:
            logging.warning(f"Error processing {symbol}: {e}")
    sorted_candidates = sorted(candidates, key=lambda x: (-x[1], -x[2]))
    return [(sym[0], sym[3], sym[0], sym[1], sym[2], sym[3]) for sym in sorted_candidates[:20]]

# Generate a base64 chart image
def generate_chart(symbol):
    df = yf.download(symbol, period="5d", interval="1h")
    if df.empty or 'Close' not in df or df['Close'].isna().any():
        return ""
    plt.figure(figsize=(10, 3))
    plt.plot(df.index, df["Close"], label="Close Price")
    plt.title(f"{symbol} Price Chart")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.grid(True)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return f'<img src="data:image/png;base64,{encoded}" style="width:100%; max-width:600px;"/>'

# Web HTML output
def generate_html():
    price_ranges = [(0, 5), (5, 20), (20, 50)]
    html = '''
    <html><head><meta http-equiv="refresh" content="3">
    <style>
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { padding: 8px 12px; border: 1px solid #ccc; text-align: left; }
tr:nth-child(even) { background-color: #f9f9f9; }
    body { font-family: Arial; background: #f4f4f4; padding: 20px; }
    h1 { color: #333; }
    h2 { color: #666; margin-top: 40px; }
    ul { background: #fff; padding: 10px; border-radius: 5px; }
    li { padding: 5px 0; }
    .bullish { color: green; font-weight: bold; }
    .bearish { color: red; font-weight: bold; }
    </style><title>Stock Screener</title></head><body><h1>MACD Screener</h1>
    '''
    if not within_trading_hours():
        html += "<p style='color:red;'>Outside trading hours (9:30 AM - 11:00 AM)</p></body></html>"
        return html.encode("utf-8")
    for min_price, max_price in price_ranges:
        candidates = screen_stocks_by_price_range(min_price, max_price)
        html += f"<h2>Stocks between ${min_price} and ${max_price}</h2><ul>"
        if not candidates:
            html += "<li>No suitable stocks found.</li>"
        else:
            html += "<table><tr><th>Ticker</th><th>Direction</th><th>Volatility</th><th>Volume</th><th>Chart</th></tr>"
        for sym, direction, ticker, vol, volm, dirn in candidates:
                cls = "bullish" if direction == "Bullish" else "bearish"
                cls = "bullish" if dirn == "Bullish" else "bearish"
            html += f"<tr><td>{sym}</td><td class='{cls}'>{dirn}</td><td>{vol:.4f}</td><td>{int(volm):,}</td><td>{generate_chart(sym)}</td></tr>"
        html += "</table>"
    html += "</body></html>"
    return html.encode("utf-8")

# HTTP handler
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(generate_html())

# Web server entry point
def start_web_server():
    PORT = 0
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        PORT = httpd.server_address[1]
        logging.info(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()

# Run server in background thread
if __name__ == "__main__":
    threading.Thread(target=start_web_server, daemon=True).start()
    while True:
        time.sleep(3)


# MACD Backtest Strategy
class MACDStrategy(bt.Strategy):
    def __init__(self):
        macd = bt.ind.MACD()
        self.crossover = bt.ind.CrossOver(macd.macd, macd.signal)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.sell()

# Backtest a given ticker
def run_backtest(ticker):
    logging.info(f"Running backtest for {ticker}")
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MACDStrategy)
    df = yf.download(ticker, start='2023-01-01', end='2023-12-31')
    if df.empty or 'Close' not in df.columns:
        logging.warning(f"No data for {ticker}")
        return
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.broker.set_cash(10000)
    cerebro.run()
    cerebro.plot()

# Run backtest for top candidate in each price range
if __name__ == '__main__':
    threading.Thread(target=start_web_server, daemon=True).start()

    # Give the server a head start before running backtests
    time.sleep(2)

    top_candidates = []
    for min_price, max_price in [(0, 5), (5, 20), (20, 50)]:
        candidates = screen_stocks_by_price_range(min_price, max_price)
        if candidates:
            top_candidates.append(candidates[0][0])  # only symbol

    for symbol in top_candidates:
        run_backtest(symbol)

    while True:
        time.sleep(3)
