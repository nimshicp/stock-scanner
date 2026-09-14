# 🚀 NIFTY 500 Breakout Scanner

A fully automated, zero-touch stock screener that continuously scans the NIFTY 500 universe for 5-year historical breakouts and sends instant alerts directly to your Telegram. 

Powered by **FastAPI**, **APScheduler**, and the **FYERS v3 API**, this scanner operates entirely in the background, autonomously handling its own API token renewals and rate limits.

---

## ✨ Features

- **Autonomous Background Authentication**: Forget logging in every morning. The built-in token manager silently refreshes FYERS access tokens in the background every 24 hours.
- **True NIFTY 500 Scanner**: Completely decoupled from your personal FYERS portfolio. It automatically fetches the official NIFTY 500 index straight from the NSE and maps them to Fyers API symbols.
- **Ultra-Fast Quotes API**: Instead of downloading heavy historical data every hour, the 2-hour scan relies entirely on the lightning-fast FYERS Quotes API to check prices in batches of 50.
- **Multi-Alert Logic**: You don't just get one alert per day. If a stock breaks out and *continues* to surge higher throughout the day, the scanner will alert you at every subsequent 2-hour check to highlight upward momentum.
- **Fort Knox Security**: Zero sensitive tokens exposed to the frontend or saved in plain text files. All API credentials and tokens are strictly locked inside a local SQLite database.
- **Smart Rate-Limiting**: The heavy 5-year historical data initial fetch algorithm is strictly throttled to completely bypass Fyers History API bans.

---

## 🏗️ System Architecture & Workflow

The system is broken into three distinct, highly decoupled workflows:

### 1. The Autonomous Token Manager
To fetch data from FYERS, the system requires a valid Access Token (expires daily). 
Before any API call, the system checks the `fyers_tokens` database. If the token is expired, the server makes a silent, headless POST request to FYERS to exchange its Master Refresh Token for a fresh Access Token. The scanner instantly resumes.

### 2. The Universe Sync & History Cache
When triggered, the background worker:
1. Downloads `ind_nifty500list.csv` from the NSE.
2. Formats them into FYERS standard (`NSE:RELIANCE-EQ`) and saves them to the `watchlist` database.
3. Loops through all 501 stocks, pausing for 1.5 seconds between each to respect the FYERS 200 req/min rate limit.
4. Fetches exactly 5 years of daily candles, calculates the absolute highest price, and permanently caches that number in the `historical_highs` database.

### 3. The 2-Hour Quotes Scan
At exactly **09:30, 11:30, 13:30, and 15:30 IST**, the APScheduler wakes up:
1. It fetches all 501 stocks from the local database.
2. It hits the FYERS Quotes API in batches of 50 (taking only 10 total API calls).
3. It compares the live Last Traded Price (LTP) to both the `5-year high` AND the `previous_ltp` (the price it was at during the last alert).
4. If it's a true breakout, it fires a Telegram message and updates the `previous_ltp` state in the database.

---

## 🗄️ Database Schema (`scanner.db`)

All state is safely managed in local SQLite.

- **`watchlist`**: Contains the NIFTY 500 universe, an `is_active` toggle, and a `previous_ltp` column to track momentum and prevent duplicate alerts for flat price action.
- **`historical_highs`**: Acts as an ultra-fast local memory cache. Stores the stock symbol and the absolute highest price reached in the trailing 5 years.
- **`fyers_tokens`**: A highly restricted, single-row table containing your encrypted FYERS Access Token, Refresh Token, and exact Unix expiration timestamps.
- **`alerts_log`**: A receipt ledger that quietly records every single Telegram alert sent.

---

## ⚙️ Installation & Setup

1. **Clone the repository and enter the directory:**
    ```bash
    cd stock-scanner
    ```

2. **Set up your Python virtual environment:**
    ```bash
    python -m venv .venv312
    .\.venv312\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure your Environment Variables:**
    Rename `.env.example` to `.env` and fill in your FYERS API keys and Telegram Bot credentials:
    ```ini
    FYERS_CLIENT_ID=your_client_id
    FYERS_SECRET_KEY=your_secret_key
    FYERS_REDIRECT_URI=http://localhost:8000/callback
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    TELEGRAM_CHAT_ID=your_telegram_chat_id
    ```
    *Note: Ensure your FYERS API Dashboard has the exact same Redirect URI configured.*

---

## 🚀 How to Run

1. **Start the FastAPI Server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

2. **Authenticate with FYERS (First Time Only):**
    Open your browser and navigate to:
    `http://localhost:8000/api/auth/login`
    After a successful login, you will be redirected back, and your Master Refresh Token will be saved to the database.

3. **Initialize the NIFTY 500 Universe:**
    Navigate to:
    `http://localhost:8000/api/universe/sync`
    This will instantly kick off the background job to fetch the NIFTY 500 stocks and calculate their 5-year highs. Check your terminal output to watch it run!

4. **Leave it running!**
    The server is now fully autonomous. It will automatically renew its own FYERS tokens every 24 hours, and it will execute the Quotes scan at 09:30, 11:30, 13:30, and 15:30 every weekday.

---

## ⚠️ Important Note on FYERS Refresh Tokens

While the system is fully automated day-to-day, **FYERS strictly enforces a 15-day maximum lifespan on Master Refresh Tokens.**
If you shut down your server for 16 consecutive days, the refresh token will permanently expire. If this happens, you will see an error in your terminal, and you will simply need to visit `http://localhost:8000/api/auth/login` to re-authenticate and start a new 15-day cycle.
