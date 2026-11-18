# Real-Time Climate and Disaster Risk Intelligence Platform

A Streamlit dashboard for county flood and hurricane information, historical weather, and social vulnerability across Texas, Louisiana, Mississippi, Alabama, and Florida.

## Dashboard sections

- **Gulf Coast Risk Dashboard:** county map, flood and hurricane scores, saved forecast snapshots, past events, and 2022 CDC/ATSDR social vulnerability information.
- **Historical Weather:** station selection and map, annual average maximum temperature, observed annual rainfall, seasonal rainfall, and heavy-rain days.
- **County Rainfall EDA:** historical three-day rainfall thresholds alongside county social vulnerability, with county highlighting and rainfall mapping.

The historical weather section also includes a five-station rainfall comparison and a fixed Houston rainfall case study for Hurricane Harvey. The comparison uses its own year range. The case study uses its own station and dates.

## Install and run

Use Python 3.11. To get an existing local copy up to date:

```bash
git switch dashboard
git pull --ff-only origin dashboard
```

Activate your project environment. If you already use the project Conda environment, run `conda activate disaster311`. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501.

## Data files

The following supporting files are included in the repository:

| File | Purpose |
| --- | --- |
| `processed/gulf_coast_stations_official.csv` | Weather station names and coordinates |
| `data/processed/svi_gulf_coast_counties.csv` | County social vulnerability ranks |
| `data/processed/gulf_coast_counties.geojson` | County boundaries |
| `data/processed/station_county_mapping_with_match_method.csv` | Station-to-county mapping |

The full processed weather dataset is distributed separately. Place it at:

```text
data/processed/gulf_coast_historical.parquet
```

The Parquet file is excluded from Git. Rainfall is already in millimeters and temperature is already in degrees Celsius. The app embeds the county rainfall summary and the county risk interface with a timestamped fallback snapshot. A saved snapshot is not a continuously refreshed forecast; check the date and freshness information displayed in the interface.

## Interpreting the charts

- Annual charts require at least 330 valid daily observations for their variable. The current UTC year and future years are excluded. The short Harvey case-study window is checked separately.
- Missing observations stay unavailable. Rainfall totals cover observed days without estimating missing rainfall.
- Average maximum temperature is the average of daily maximum temperatures, not the average temperature throughout the day.
- A heavy-rain day means at least 50 mm at a station. It does not confirm that a flood occurred.
- Five-station annual comparisons use shared years with at least 330 valid rainfall days at every station. Seasonal charts also require at least 80% of the calendar days observed in each contributing month-year. Month-year daily means receive equal weight.
- Partial-decade labels identify the first and last shared years included. A single year is labelled explicitly.
- The historical three-day rainfall percentile is a descriptive statistic, not a forecast or a flood probability.
- SVI describes relative social vulnerability. It is separate from hazard probability and does not change the model predictions.
- Station records describe the station location; they do not automatically represent an entire county.

## Filters

State and county selections narrow available station choices. The station and year controls apply to the station history. In County Rainfall EDA, the state controls the comparison area and the county selects a highlight. The five-station comparison and Harvey case study explain their independent controls in the interface.

## Team review

Dashboard development is shared on the `dashboard` branch. Merge into `main` after team review. Sharing this branch allows teammates to run the app locally; hosting a public Streamlit app is a separate deployment step.
