@echo off
REM Get current time in 24-hour format (HH:mm)
for /f "tokens=1 delims=:" %%H in ("%time%") do set /a "hour=10%%H %% 100"

REM Check if the current time is after 4:30 PM (16:30) IST
if %hour% geq 18 (
    echo Skipping data extraction script because the current time is after 6:00 PM IST.
) else (
    REM Run data extractor script
    python load_stocks_data.py
)

REM Launch Streamlit app
streamlit run webapp.py
