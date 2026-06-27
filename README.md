# Yahoo Finance O-X-A-B-C Pattern Scanner

A Streamlit app that accepts Yahoo Finance URLs or tickers and scans for the O-X-A-B-C swing pattern from the sketch.

## What it scans for

Default bullish shape:

`O high → X low → A high → B low → C high`

Default bearish inverse:

`O low → X high → A low → B high → C low`

Default Fibonacci ranges:

- `XA / OX`: 0.50 to 0.618
- `AB / XA`: 1.13 to 1.618
- `BC / AB`: 1.618 to 2.27

The app lets you tune all of these ranges in the sidebar.

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy as a web app on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload these files to the repository.
3. Go to Streamlit Community Cloud.
4. Create a new app from the repository.
5. Set the main file path to `app.py`.
6. Deploy.

## Notes

- This app uses `yfinance` to download Yahoo Finance price data.
- Internet access is required when the app runs.
- The scanner is for research and learning, not financial advice.
- Pattern detection is sensitive to the settings. Try changing lookback, minimum swing size, and tolerance when no matches are found.
