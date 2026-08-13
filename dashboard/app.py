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

location = st.sidebar.selectbox(
    "Select location",
    ["Houston, Texas"],
)

st.sidebar.info(
    "More locations and live risk data will be added as the project develops."
)

# Temporary summary cards
st.subheader("Risk Summary")

column1, column2, column3 = st.columns(3)

column1.metric("Selected Location", location)
column2.metric("Disaster Type", disaster_type)
column3.metric("Current Risk", "Not available yet")

# Houston Intercontinental Airport coordinates
houston_data = pd.DataFrame(
    {
        "Location": ["Houston Intercontinental Airport"],
        "latitude": [29.9844],
        "longitude": [-95.3414],
    }
)

# Convert the location into a GeoPandas GeoDataFrame
houston_geometry = [
    Point(longitude, latitude)
    for longitude, latitude in zip(
        houston_data["longitude"],
        houston_data["latitude"],
    )
]

houston_gdf = gpd.GeoDataFrame(
    houston_data,
    geometry=houston_geometry,
    crs="EPSG:4326",
)

# Houston map
st.subheader("Houston Weather Station Map")

map_layer = pdk.Layer(
    "ScatterplotLayer",
    data=houston_gdf,
    get_position="[longitude, latitude]",
    get_color="[255, 80, 60, 200]",
    get_radius=2500,
    pickable=True,
)

map_view = pdk.ViewState(
    latitude=29.9844,
    longitude=-95.3414,
    zoom=9,
    pitch=0,
)

st.pydeck_chart(
    pdk.Deck(
        layers=[map_layer],
        initial_view_state=map_view,
        tooltip={"text": "{Location}"},
    )
)

## Load NOAA Houston weather data
@st.cache_data
def load_weather_data():
    url = (
        "https://www.ncei.noaa.gov/data/"
        "global-historical-climatology-network-daily/access/"
        "USW00012960.csv"
    )

    data = pd.read_csv(
        url,
        usecols=["DATE", "TMAX", "PRCP"],
    )

    data["DATE"] = pd.to_datetime(data["DATE"])
    data["TMAX"] = data["TMAX"] / 10
    data["PRCP"] = data["PRCP"] / 10

    return data


st.subheader("Climate Visualizations")

try:
    weather_data = load_weather_data()
    weather_data["Year"] = weather_data["DATE"].dt.year

    yearly_counts = weather_data.groupby("Year")["TMAX"].count()
    complete_years = yearly_counts[yearly_counts >= 330].index

    weather_data = weather_data[
        weather_data["Year"].isin(complete_years)
    ]

    yearly_temperature = (
        weather_data
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
    weather_data
    .groupby("Year", as_index=False)["PRCP"]
    .sum()
)

    rainfall_chart = px.bar(
        yearly_rainfall,
        x="Year",
        y="PRCP",
        title="Yearly Total Rainfall",
        labels={
            "PRCP": "Total Rainfall (mm)"
        },
        color_discrete_sequence=["royalblue"],
    )

    st.plotly_chart(rainfall_chart, width="stretch")
    extreme_heat = (
        weather_data
        .assign(Extreme_Heat=weather_data["TMAX"] >= 35)
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
except Exception as error:
    st.error(f"Unable to load NOAA data: {error}")

st.subheader("County-Level Disaster Risk")
st.info("Model-generated county risk scores will be added here.")