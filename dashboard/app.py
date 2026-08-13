import geopandas as gpd
import pandas as pd
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

# Future dashboard sections
st.subheader("Climate Visualizations")
st.info("Temperature, rainfall, and extreme-weather charts will be added here.")

st.subheader("County-Level Disaster Risk")
st.info("Model-generated county risk scores will be added here.")