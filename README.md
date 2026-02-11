# Dash Options Chain Live Dashboard

A real-time interactive dashboard for visualizing **options chains** of stocks/ETFs (SPY, GLD, QQQ, AAPL, TSLA, etc.) with the following plots:

- Volatility Skew  
- Volatility Smile  
- Delta Profile  
- Open Interest (side-by-side bars for calls/puts)  
- Trading Volume (side-by-side bars)  
- Gamma Exposure Profile  

Data is pulled from **Yahoo Finance** via `yfinance` and updated automatically every 10 seconds. Built with **Dash + Plotly**.

### Features
  
- Simplified Black-Scholes Greeks calculation (Delta & Gamma)  
- Side-by-side bars for Open Interest & Volume (much easier to read than overlapping lines)  
- Live refresh every 10 seconds (interval is configurable)  
- Full Plotly interactivity: zoom, hover, pan, box select, etc.  
- Currently defaults to the nearest expiry (often 0DTE on highly liquid underlyings like SPY)

### Requirements

- Python 3.9 or higher  
- See `requirements.txt`

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/dash-options-chain-live.git
cd dash-options-chain-live

# 2. (Recommended) Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
# or on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the dashboard
python options_dashboard_dark.py
