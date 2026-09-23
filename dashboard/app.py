from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from shapely.geometry import Point


# Configure the dashboard page
st.set_page_config(
    page_title="Climate & Disaster Risk Dashboard",
    page_icon="🌎",
    layout="wide",
)

# Dashboard heading
st.title("🌎 Climate & Disaster Risk Intelligence Dashboard")
st.write(
    "An interactive dashboard for exploring weather patterns and "
    "future disaster-risk predictions."
)

# Sidebar controls
st.sidebar.header("Dashboard Filters")

disaster_type = st.sidebar.selectbox(
    "Select disaster type",
    ["Extreme Heat", "Flood", "Wildfire", "Severe Storm"],
)

# Resolve the CSV relative to the project, regardless of terminal directory.
STATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "processed"
    / "gulf_coast_stations_official.csv"
)


def load_station_list(path):
    stations = pd.read_csv(path, dtype={"ID": str})
    required = {"ID", "NAME", "STATE", "LATITUDE", "LONGITUDE"}
    missing = required - set(stations.columns)
    if missing:
        raise ValueError(f"Station list is missing columns: {', '.join(sorted(missing))}")
    if stations.empty or stations[list(required)].isna().any().any():
        raise ValueError("Station list is empty or has missing station details.")
    if stations["ID"].duplicated().any():
        raise ValueError("Station list contains duplicate station IDs.")
    if not stations["ID"].str.fullmatch(r"[A-Z0-9]{11}").all():
        raise ValueError("Station list contains an invalid NOAA station ID.")
    for column, limit in [("LATITUDE", 90), ("LONGITUDE", 180)]:
        stations[column] = pd.to_numeric(stations[column], errors="raise")
        if not stations[column].between(-limit, limit).all():
            raise ValueError(f"Station list has invalid {column} values.")
    return stations.sort_values(["STATE", "NAME", "ID"]).reset_index(drop=True)


try:
    stations = load_station_list(STATION_FILE)
except FileNotFoundError:
    st.error("The station-list CSV is missing. Generate it before running the dashboard.")
    st.code("python scripts/00_get_official_station_list.py", language="bash")
    st.stop()
except (ValueError, OSError) as error:
    st.error(f"Unable to read the station list: {error}")
    st.stop()

# Filter the station dropdown by state; keep all stations available by default.
STATE_NAMES = {
    "AL": "Alabama",
    "FL": "Florida",
    "LA": "Louisiana",
    "MS": "Mississippi",
    "TX": "Texas",
}
selected_state = st.sidebar.selectbox(
    "Select state",
    ["All states"] + sorted(stations["STATE"].unique().tolist()),
    format_func=lambda state: (
        "All states" if state == "All states"
        else f"{STATE_NAMES.get(state, state)} ({state})"
    ),
)
filtered_stations = (
    stations if selected_state == "All states"
    else stations.loc[stations["STATE"] == selected_state]
)
station_ids = filtered_stations["ID"].tolist()
station_labels = {
    row.ID: f"{row.NAME}, {row.STATE} ({row.ID})"
    for row in stations.itertuples()
}
selected_station_id = st.sidebar.selectbox(
    "Select weather station",
    station_ids,
    index=station_ids.index("USW00012960") if "USW00012960" in station_ids else 0,
    format_func=lambda station_id: station_labels[station_id],
)
selected_station = stations.loc[stations["ID"] == selected_station_id].iloc[0]
location = f"{selected_station['NAME']}, {selected_station['STATE']}"
st.sidebar.caption(
    f"{len(filtered_stations):,} stations shown out of "
    f"{len(stations):,} Gulf Coast weather stations."
)
st.sidebar.info(
    "Historical charts load only the selected station. "
    "Disaster-type selection is for future risk forecasts; it does not filter these charts."
)

# Temporary summary cards
st.subheader("Risk Summary")

column1, column2, column3 = st.columns(3)

column1.metric("Selected Location", location)
column2.metric("Disaster Type", disaster_type)
column3.metric("Current Risk", "Not available yet")

# Use the selected station's coordinates for the GeoPandas map.
station_data = pd.DataFrame({
    "Location": [location],
    "ID": [selected_station_id],
    "latitude": [float(selected_station["LATITUDE"])],
    "longitude": [float(selected_station["LONGITUDE"])],
})
station_gdf = gpd.GeoDataFrame(
    station_data,
    geometry=[Point(station_data.iloc[0]["longitude"], station_data.iloc[0]["latitude"])],
    crs="EPSG:4326",
)
st.subheader("Selected Weather Station Map")
st.caption(station_labels[selected_station_id])
map_layer = pdk.Layer(
    "ScatterplotLayer",
    data=station_gdf,
    get_position="[longitude, latitude]",
    get_color="[255, 80, 60, 200]",
    get_radius=2500,
    pickable=True,
)
map_view = pdk.ViewState(
    latitude=float(selected_station["LATITUDE"]),
    longitude=float(selected_station["LONGITUDE"]),
    zoom=9,
    pitch=0,
)
st.pydeck_chart(pdk.Deck(
    layers=[map_layer],
    initial_view_state=map_view,
    tooltip={"text": "{Location}\n{ID}"},
))

# Read only the selected station and chart columns from the processed dataset.
WEATHER_FILE = (
    Path(__file__).resolve().parents[1]
    / "data" / "processed" / "gulf_coast_historical.parquet"
)


@st.cache_data(max_entries=32)
def load_weather_data(station_id, file_path, file_version):
    # file_version invalidates cached records when the dataset is replaced.
    data = pd.read_parquet(
        file_path,
        engine="pyarrow",
        columns=["DATE", "TMAX", "PRCP"],
        filters=[("STATION", "==", station_id)],
    )
    if data.empty:
        raise ValueError(f"No processed weather records found for {station_id}.")
    data["DATE"] = pd.to_datetime(data["DATE"], errors="raise")
    if data["DATE"].isna().any() or data["DATE"].duplicated().any():
        raise ValueError("Selected station has missing or duplicate observation dates.")
    for column in ["TMAX", "PRCP"]:
        data[column] = pd.to_numeric(data[column], errors="raise")
    # The processed dataset already stores temperature in °C and rainfall in mm.
    return data.sort_values("DATE").reset_index(drop=True)


st.subheader("Climate Visualizations")

try:
    with st.spinner("Loading weather records for the selected station…"):
        file_info = WEATHER_FILE.stat()
        weather_data = load_weather_data(
            selected_station_id, str(WEATHER_FILE),
            (file_info.st_mtime_ns, file_info.st_size),
        )
    weather_data["Year"] = weather_data["DATE"].dt.year

    # Apply coverage separately: temperature coverage cannot validate rainfall.
    closed_years = weather_data["Year"] < pd.Timestamp.now(tz="UTC").year
    weather_data = weather_data.loc[closed_years].copy()
    # Reset the year selection for each station, whose history may differ.
    selected_year_range = None
    if not weather_data.empty:
        first_year = int(weather_data["Year"].min())
        last_year = int(weather_data["Year"].max())
        if first_year < last_year:
            selected_year_range = st.sidebar.slider(
                "Select year range",
                min_value=first_year,
                max_value=last_year,
                value=(first_year, last_year),
                step=1,
                key=f"year_range_{selected_station_id}",
                help="Filters all historical charts. Years still need at least 330 valid observations per variable.",
            )
        else:
            selected_year_range = (first_year, last_year)
            st.sidebar.caption(f"Available historical year: {first_year}")
        start_year, end_year = selected_year_range
        weather_data = weather_data.loc[
            weather_data["Year"].between(start_year, end_year)
        ].copy()
    else:
        st.sidebar.caption("No observations before the current year are available.")

    counts = weather_data.groupby("Year")[["TMAX", "PRCP"]].count()
    temperature_years = counts.index[counts["TMAX"] >= 330]
    rainfall_years = counts.index[counts["PRCP"] >= 330]
    temperature_data = weather_data[weather_data["Year"].isin(temperature_years)]
    rainfall_data = weather_data[weather_data["Year"].isin(rainfall_years)]
    st.caption(
        f"Historical observations for {location} ({selected_station_id}). "
        "Source: processed NOAA dataset. Current year excluded. Each chart requires at least 330 valid daily "
        "observations per year for its variable. Rainfall totals and heat-day "
        "counts cover observed days only; qualifying years may still have gaps."
    )
    if selected_year_range is not None:
        st.caption(f"Selected years: {start_year}–{end_year} (inclusive).")
    if temperature_data.empty:
        st.warning("No years meet the temperature coverage requirement in the selected period.")
    if rainfall_data.empty:
        st.warning("No years meet the rainfall coverage requirement in the selected period.")

    yearly_temperature = (
        temperature_data
        .groupby("Year", as_index=False)["TMAX"]
        .mean()
    )

    temperature_chart = px.line(
        yearly_temperature,
        x="Year",
        y="TMAX",
        markers=True,
        title="Yearly Average Maximum Temperature",
        labels={
            "TMAX": "Average Maximum Temperature (°C)"
        },
    )

    st.plotly_chart(temperature_chart, width="stretch")
    yearly_rainfall = (
        rainfall_data
        .groupby("Year", as_index=False)["PRCP"]
        .sum(min_count=1)
    )

    rainfall_chart = px.bar(
        yearly_rainfall,
        x="Year",
        y="PRCP",
        title="Yearly Rainfall Total (Observed Days)",
        labels={
            "PRCP": "Total Rainfall (mm)"
        },
        color_discrete_sequence=["royalblue"],
    )

    st.plotly_chart(rainfall_chart, width="stretch")
    extreme_heat = (
        temperature_data
        .assign(Extreme_Heat=temperature_data["TMAX"] >= 35)
        .groupby("Year", as_index=False)["Extreme_Heat"]
        .sum()
    )

    heat_chart = px.bar(
        extreme_heat,
        x="Year",
        y="Extreme_Heat",
        title="Extreme Heat Days by Year",
        labels={
            "Extreme_Heat": "Number of Days with TMAX ≥ 35°C"
        },
        color_discrete_sequence=["tomato"],
    )

    st.plotly_chart(heat_chart, width="stretch")
except FileNotFoundError:
    st.error(
        "Weather dataset missing. Place gulf_coast_historical.parquet in "
        "the project's data/processed folder."
    )
except Exception as error:
    st.error(f"Unable to load processed weather data: {error}")

st.subheader("County-Level Disaster Risk")
st.info("Model-generated county risk scores will be added here.")