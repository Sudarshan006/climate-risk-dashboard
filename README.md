# climate-risk-dashboard
Real- Time Climate Disaster Risk Platform


## Dashboard features

- Choose from 523 Gulf Coast weather stations.
- View the selected station on a map.
- Explore yearly average maximum temperature, rainfall totals, and extreme heat days (TMAX ≥ 35°C).
- County-level risk predictions are not yet connected.

## Required data

Obtain the full processed dataset from the data engineer and place it at:

`data/processed/gulf_coast_historical.parquet`

The station list is stored at:

`processed/gulf_coast_stations_official.csv`

The full Parquet dataset is shared separately and excluded from Git.
Temperatures are already in °C and rainfall in mm.

## Run the dashboard

With dependencies installed, run these commands from the project folder using the existing Conda environment:

```bash
conda activate disaster311
python -m streamlit run dashboard/app.py
```

Open http://localhost:8501 in your browser.

Dependencies are listed in requirements.txt, including PyArrow for reading Parquet files.

## Data limitations

- The current year is excluded.
- Each chart requires at least 330 valid daily observations per year for its variable.
- Rainfall totals and heat-day counts cover observed days only. Missing days can cause underestimation.
- These charts show historical observations, not forecasts.
- The disaster-type selector does not filter the historical charts.