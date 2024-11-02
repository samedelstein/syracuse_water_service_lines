import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import plotly.express as px
from datetime import datetime


# Create DataFrame
water_services_df = pd.read_csv('Water_Services.csv')
def convert_date(value):
    parts = value.split("/")
    
    # Handle "0/000" or any other clearly invalid date as NaT
    if value == "0/000" or len(parts) != 2 or not parts[1].isdigit():
        return pd.NaT

    # Check and correct month part
    month = parts[0]
    year = parts[1]
    
    # Default to January if month is not a valid number from 1 to 12
    if not month.isdigit() or not (1 <= int(month) <= 12):
        month = "01"
    
    # Correct year format for three-digit years by assuming they're from the 1900s
    if len(year) == 3:
        year = "19" + year.lstrip("0")  # Assume 1900s and strip leading zero
    
    # Combine corrected month and year and convert to datetime
    corrected_value = f"{int(month):02}/{year}"
    return pd.to_datetime(corrected_value, format="%m/%Y", errors='coerce')

# Apply the function to the SERV_INSTALL column and set the service_install_date column
water_services_df['service_install_date'] = water_services_df['SERV_INSTALL'].apply(convert_date)
water_services_df['PTYPE'] = water_services_df['PTYPE'].str.strip()

# Convert DataFrame to GeoDataFrame
gdf = gpd.GeoDataFrame(
    water_services_df,
    geometry=gpd.points_from_xy(water_services_df['X'], water_services_df['Y']),
    crs="EPSG:4326"  # Set CRS to WGS84
)

# Define a consistent color scheme for each material type (PTYPE)
color_map = {
    "COPPER": [255, 0, 0, 160],       # Red with opacity
    "LEAD": [128, 0, 128, 160],       # Purple with opacity
    "OTHER": [128, 128, 128, 160],    # Gray with opacity
    "GAL.IRON": [0, 128, 128, 160],   # Teal with opacity
    "CAST IRON": [255, 165, 0, 160],  # Orange with opacity
    "DUCTILE": [0, 0, 255, 160],      # Blue with opacity
    "PVC": [0, 128, 0, 160]           # Green with opacity
}

# Map color column based on cleaned PTYPE values
gdf['color'] = gdf['PTYPE'].map(color_map)

# Main title
st.title("Service Line Installation Dashboard")

# Collapsible data quality findings and dataset link
with st.expander("Data Quality Findings and Assumptions"):
    st.markdown("""
    **Data Quality Findings**:

    - **Future Dates for Installation**: Some installation dates are in the future, which doesn’t align with the expectation that installation dates should be historical. This suggests possible data entry errors or placeholder dates that were not updated.
    - **Messy and Inconsistent Date Formats**: Dates were provided in various formats, including cases where months were missing or invalid. These were normalized to the first of the month when missing, but this assumption may not always be correct.
    - **Lead Pipe Installations Post-1986**: Some records indicate lead pipes being installed after the 1986 federal ban, likely due to either outdated information or data entry errors. Such records should be verified as they can mislead material analysis.
    - **Default Month Assumptions**: When the month was missing (e.g., "0/2000"), we assumed January as the default. However, this may not reflect the actual installation timing.

    For more information and to access the dataset, [click here](https://data.syr.gov/datasets/e1deb6e9e4b74071af272982d8f9994e_0/explore).
    """)
# Map of service lines by year
st.subheader("Service Line Installations by Year Range")

# Set initial year range for the data
min_year = int(gdf['service_install_date'].dt.year.min())
max_year = int(gdf['service_install_date'].dt.year.max())

# Map: Range slider for selecting year range
year_range = st.slider("Select Year Range", min_year, max_year, (min_year, max_year))

# Filter data based on selected year range
filtered_data = gdf[(gdf['service_install_date'].dt.year >= year_range[0]) & 
                    (gdf['service_install_date'].dt.year <= year_range[1])]

# Display map with pydeck and tooltip
if not filtered_data.empty:
    # Create Pydeck Layer for colored points based on PTYPE, with tooltip information
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=filtered_data,
        get_position=["X", "Y"],
        get_fill_color="color",
        get_radius=100,
        pickable=True,
    )
    
    # Define tooltip content
    tooltip = {
        "html": "<b>Address:</b> {TAP_ADDRESS}<br/>"
                "<b>Type:</b> {PTYPE}<br/>"
                "<b>Service Type:</b> {STYP}<br/>"
                "<b>Install Date:</b> {service_install_date}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    # Set the viewport location for the map
    view_state = pdk.ViewState(
        latitude=filtered_data["Y"].mean(),
        longitude=filtered_data["X"].mean(),
        zoom=12,
        pitch=0,
    )

    # Display the map with tooltip
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
else:
    st.write("No data available for the selected year range.")

# Bar chart: Range slider for selecting year range
st.subheader("Installations by Year and Material Type")
bar_year_range = st.slider("Select Year Range for Bar Chart", min_year, max_year, (min_year, max_year), key="bar_slider")

# Filter data for bar chart based on the selected range
bar_data = water_services_df[(water_services_df['service_install_date'].dt.year >= bar_year_range[0]) & 
                             (water_services_df['service_install_date'].dt.year <= bar_year_range[1])]

# Group by year and PTYPE for the stacked bar chart
yearly_counts = bar_data.groupby([bar_data['service_install_date'].dt.year, 'PTYPE']).size().unstack().fillna(0)

# Create the bar chart with Plotly, using the same color scheme
fig = px.bar(
    yearly_counts, 
    barmode='stack', 
    title="Installations by Year and Material Type",
    labels={'value': 'Number of Installations', 'index': 'Year'},
    color_discrete_map={
        "COPPER": "rgb(255,0,0)",          # Red
        "LEAD": "rgb(128,0,128)",          # Purple
        "OTHER": "rgb(128,128,128)",       # Gray
        "GAL.IRON": "rgb(0,128,128)",      # Teal
        "CAST IRON": "rgb(255,165,0)",     # Orange
        "DUCTILE": "rgb(0,0,255)",         # Blue
        "PVC": "rgb(0,128,0)"              # Green
    }
)

# Display bar chart
st.plotly_chart(fig)