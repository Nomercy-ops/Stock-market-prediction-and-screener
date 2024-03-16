import asyncio
import yfinance as yf
import pandas as pd
import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_data_batch(symbols_batch, conn):
    tasks = [fetch_data(symbol, conn) for symbol in symbols_batch]
    await asyncio.gather(*tasks)

async def fetch_data(symbol, conn):
    try:
        # Fetch data from Yahoo Finance
        data = yf.download(symbol, period='max')

        # Prepare data for insertion into the database
        if not data.empty:
            data.reset_index(inplace=True)
            data['Symbols'] = symbol

            # Insert data into the database
            data.to_sql('stock_price', conn, if_exists='append', index=False)

            logger.info(f"Data for symbol {symbol} inserted successfully.")
        else:
            logger.warning(f"No data available for symbol {symbol}.")
    except Exception as e:
        logger.error(f"Error fetching data for symbol {symbol}: {e}")

async def main():
    # Load symbols from symbols.csv
    try:
        symbols_df = pd.read_csv('symbols.csv')
        symbols = symbols_df['Symbol'].tolist()
        symbols = [symbol + ".NS" for symbol in symbols]
    except Exception as e:
        logger.error(f"Error loading symbols from CSV: {e}")
        return

    # Connect to SQLite database
    try:
        conn = sqlite3.connect('stock_price.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stock_price
                     (Symbol TEXT, Date TEXT, Open REAL, High REAL, Low REAL, Close REAL, Adj Close REAL, Volume INTEGER)''')
        logger.info("Connected to database successfully.")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return

    # Fetch data in batches
    batch_size = 100
    for i in range(0, len(symbols), batch_size):
        symbols_batch = symbols[i:i+batch_size]
        await fetch_data_batch(symbols_batch, conn)

    # Commit changes and close connection
    try:
        conn.commit()
        conn.close()
        logger.info("Database connection closed.")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

# Run the asyncio event loop
asyncio.run(main())
