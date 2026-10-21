# climate-risk-dashboard

Real-Time Climate Disaster Risk Platform

The current dashboard explores historical NOAA weather observations for Gulf Coast stations. Live disaster-risk predictions are not yet connected.

## Dashboard features

- Choose from 523 Gulf Coast weather stations, with a state filter to narrow the list.
- View the selected station on a map.
- Select a year range for the historical charts.
- Explore yearly average maximum temperature, rainfall totals, and extreme heat days (TMAX ≥ 35°C).
- Compare a selected year's average maximum temperature with that station's 1991–2020 reference average.
- See the reference as a green dashed line on the temperature chart when enough reference data is available.
- Inspect a data-completeness table showing valid days, missing days, coverage percentages, and whether each year is included.
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

## How the annual charts work

Selecting a station automatically loads its weather records and applies the checks below. Users do not need to check each year manually.

1. Exclude the current year and any future years, using the current UTC year.
2. Apply the selected year range to the historical charts.
3. Count valid daily observations separately for temperature (TMAX) and rainfall (PRCP).
4. Include a year in a chart only when its relevant variable has at least 330 valid daily observations.

| Chart | Calculation | Coverage requirement |
| --- | --- | --- |
| Yearly average maximum temperature | Average of the observed daily maximum temperatures | At least 330 valid TMAX days |
| Yearly rainfall total | Sum of rainfall on observed days | At least 330 valid PRCP days |
| Extreme heat days | Count of observed days with TMAX ≥ 35°C | At least 330 valid TMAX days |

A year can qualify for temperature but fail the rainfall check, or the other way around. The 35°C threshold is the project's definition of an extreme heat day; it is not an official warning level.

## Temperature comparison with 1991–2020

The reference is calculated separately for each station:

1. Take the station's records from 1991 through 2020.
2. Keep years with at least 330 valid TMAX observations.
3. Require at least 24 qualifying years out of the 30-year period.
4. Calculate the average maximum temperature for each qualifying year, then average those yearly values with equal weight.

The 330-day and 24-year thresholds are project rules. This is a **project reference, not an official NOAA climate normal**.

Under **Temperature compared with historical average**, choose a qualifying year using **Year to compare**. The dashboard shows:

- The selected year's average daily maximum temperature.
- The station's 1991–2020 reference average.
- The difference: selected-year average minus reference average.

For example, a yearly value of 28°C and a reference of 27°C gives a difference of +1°C. A positive difference means warmer than the reference; a negative difference means cooler. This comparison does not assign a disaster-risk level.

The reference uses the full available 1991–2020 period and does not change when the year-range slider changes. The comparison-year choices follow the slider and include only qualifying temperature years. If fewer than 24 reference years qualify, the reference and difference are shown as unavailable.

Open **Which reference years are included?** to see which reference years passed or failed the coverage check. The green dashed line marks the reference average; green does not mean safe or low risk. Values are displayed to two decimal places, while differences are calculated before rounding.

## Data-completeness table

Open **Data completeness for the selected years** below the comparison section. It lists every year in the selected range, including years with no observations.

- **Valid days:** days with a non-missing measurement for that variable.
- **Missing days:** calendar days minus valid days, including absent dates and missing measurements.
- **Coverage percentage:** valid days divided by 365 days, or 366 in a leap year, multiplied by 100.
- **Included or excluded:** whether that variable meets the 330-day rule for the year.

For example, 330 valid days in a 365-day year means 35 missing days and about 90.4% coverage. That year qualifies, but its record is still incomplete. Temperature coverage also determines whether the year appears in the heat-day chart.

## Data limitations

- These charts show historical observations, not forecasts or real-time warnings.
- The disaster-type selector does not filter the historical charts; it is intended for future risk forecasts.
- The coverage rules reduce the use of incomplete records but do not guarantee an unbiased annual result. Missing observations in a particular season can affect temperature averages.
- Rainfall totals and heat-day counts cover observed days only. Missing days can cause underestimation; the dashboard does not estimate values for those days.
- Average daily maximum temperature is not the same as average temperature across the whole day.
- Available years differ by station. Some stations may not have enough data for the reference comparison.
- The map shows a weather station's location. Its measurements are not automatically representative of an entire county.
- Social vulnerability overlays, model-generated county risk scores, a RAG assistant, and automated alerts are not implemented in this dashboard version.

## Development branch

Dashboard updates are currently developed on the `dashboard` branch. Merging into `main` is a separate team review step.
