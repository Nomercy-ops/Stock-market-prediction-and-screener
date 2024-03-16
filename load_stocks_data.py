import asyncio
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

async def fetch_data_batch(symbols, conn):
    """
    Asynchronously fetches data for all symbols concurrently (loop approach).

    Args:
        symbols (list): List of symbols to fetch data for.
        conn (sqlite3.Connection): SQLite database connection.
    """
    tasks = [fetch_data(symbol, conn) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return [result for result in results if result is not None and not result.empty]

async def fetch_data(symbol, conn):
    """
    Fetches data for a single symbol.

    Args:
        symbol (str): Symbol to fetch data for.
        conn (sqlite3.Connection): SQLite database connection.
    Returns:
        pd.DataFrame: DataFrame containing fetched data.
    """
    data = None
    try:
        today = datetime.now().date()
        c = conn.cursor()
        c.execute("SELECT LastLoadTime FROM LoadHistory WHERE Symbols = ?", (symbol,))
        last_load_time = c.fetchone()
        last_load_date = datetime.strptime(last_load_time[0], "%Y-%m-%d").date() if last_load_time else None


        if last_load_date < today:
            days_difference = (today - last_load_date).days
            # Fetch data from start date to today
            start_date = last_load_date + timedelta(days=days_difference)
            start_date = datetime.combine(start_date, datetime.now().time())  # Convert to datetime object with no timezone info

            end_date = datetime.combine(today,datetime.now().time()) # Convert to datetime object with no timezone info

            print(f"Fetching data for symbol {symbol} from {start_date} to {end_date}.")
            data = yf.download(symbol, start=start_date, end=end_date)

        elif last_load_date == today:
            # Fetch data for today only
            print(f"Data for symbol {symbol} on date {today} is already present. Updating the data.")
            data = yf.download(symbol, period='1d')

        if not data.empty:
            data.reset_index(inplace=True)
            data['Symbols'] = symbol
            return data
        else:
            print(f"No data fetched for symbol {symbol}")
            return pd.DataFrame()

    except Exception as e:
        print(f"An exception occurred while fetching data for symbol {symbol}: {e}")
        return pd.DataFrame()

async def main() -> None:
    try:
        # Read symbols from CSV file
        symbols = [symbol + ".NS" for symbol in pd.read_csv('symbols.csv')['Symbol'].tolist()]
        # Connect to SQLite database
        conn = sqlite3.connect('stock_price.db', check_same_thread=False)
        try:
            # Fetch data for each symbol in smaller batches
            batch_size = 50
            all_data = []
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i+batch_size]
                batch_data = await fetch_data_batch(batch_symbols, conn)
                all_data.extend(batch_data)
            # Combine all batch data into a single DataFrame
            all_data_df = pd.concat(all_data, ignore_index=True)
            # Update data in the database
            await update_data_in_db(all_data_df, conn)
        finally:
            # Close database connection
            conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")


async def update_data_in_db(data, conn):
    """
    Updates data in the database.

    Args:
        data (pd.DataFrame): DataFrame containing data to update.
        conn (sqlite3.Connection): SQLite database connection.
    """
    today = datetime.now().date()
    if not data.empty:
        with conn:
            c = conn.cursor()
            # Delete existing data for the same date and symbols
            delete_query = "DELETE FROM stock_price WHERE Date = ?"
            c.execute(delete_query, (today,))
            conn.commit()
            # Insert data into the database
            data.to_sql('stock_price', conn, if_exists='append', index=False)
        print("Data updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
