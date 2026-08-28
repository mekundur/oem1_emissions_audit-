"""
SoSe26 Case Study - OEM1 Emissions Investigation
Group 16

Streamlit web application presenting the results of the T2 control unit
emissions investigation to OEM1 management: affected vehicle counts,
geographic distribution, and a full data table.

Data source: SoSe26_Case_Study_finalData_Group_16.csv
(must be located at Data/SoSe26_Case_Study_finalData_Group_16.csv,
relative to this script, per submission folder structure)

Run with:
    streamlit run SoSe26_Case_Study_App_Group_16.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------------
# Page config (must be the first Streamlit command)
# ------------------------------------------------------------------
st.set_page_config(
    page_title="OEM1 Emissions Investigation",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Theming: light blue accent colour + Source Sans Pro font
#
# Source Sans Pro is loaded from Google Fonts here for simplicity.
# If the submission must run fully offline / without internet access,
# download the font files instead and place them in the www/ folder,
# then reference them with a local @font-face rule (see note at the
# bottom of this block).
# ------------------------------------------------------------------
PRIMARY_LIGHT_BLUE = "#5DADE2"
PRIMARY_LIGHT_BLUE_BG = "#EAF4FB"

st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Source Sans Pro', sans-serif;
        }}

        /* Sidebar background tint */
        section[data-testid="stSidebar"] {{
            background-color: {PRIMARY_LIGHT_BLUE_BG};
        }}

        /* Metric cards */
        div[data-testid="stMetric"] {{
            background-color: {PRIMARY_LIGHT_BLUE_BG};
            border: 1px solid {PRIMARY_LIGHT_BLUE};
            border-radius: 8px;
            padding: 12px;
        }}

        /* Metric text: force dark, high-contrast colours regardless of
           Streamlit's own theme, since the light-blue card background
           needs dark text to stay readable. */
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
            color: #21618C !important;
            font-weight: 600;
        }}

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: #154360 !important;
        }}

        /* Tab highlight colour */
        .stTabs [aria-selected="true"] {{
            color: {PRIMARY_LIGHT_BLUE} !important;
            border-bottom-color: {PRIMARY_LIGHT_BLUE} !important;
        }}

        h1, h2, h3 {{
            color: #21618C;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# NOTE (offline font option):
# @font-face {
#     font-family: 'Source Sans Pro';
#     src: url('www/SourceSansPro-Regular.ttf');
# }
# ... then place the .ttf files inside the www/ submission subfolder.

# ------------------------------------------------------------------
# Data loading (cached so the file is only read once per session)
# ------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "data" / "SoSe26_Case_Study_finalData_Group_16.csv"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Zulassung"] = pd.to_datetime(df["Zulassung"], errors="coerce")

    # Coordinates are stored with a comma decimal separator (e.g. "12,746491").
    # Convert to proper floats so they can be used for mapping.
    for col in ["Laengengrad", "Breitengrad"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = (
                df[col].astype(str).str.replace(",", ".", regex=False).astype(float)
            )

    return df


df = load_data(DATA_PATH)

# ------------------------------------------------------------------
# Sidebar: logo + global filters
# (filters apply across all tabs via session state / shared df_filtered)
# ------------------------------------------------------------------
with st.sidebar:
    # Replace with your own logo file, placed in the www/ folder, e.g.:
    # st.image("www/logo.png", use_container_width=True)
    st.markdown("### OEM1 Quality Science")
    st.markdown("---")

    st.markdown("#### Filters")

    vehicle_types = sorted(df["Vehicle_Type"].dropna().unique().tolist())
    selected_types = st.multiselect(
        "Vehicle type",
        options=vehicle_types,
        default=vehicle_types,
    )

    min_date = df["Zulassung"].min()
    max_date = df["Zulassung"].max()
    date_range = st.date_input(
        "Registration date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    municipalities = sorted(df["Gemeinden"].dropna().unique().tolist())
    selected_municipalities = st.multiselect(
        "Municipality (optional)",
        options=municipalities,
        default=[],
        help="Leave empty to include all municipalities.",
    )

# Apply filters
mask = df["Vehicle_Type"].isin(selected_types)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask &= (df["Zulassung"] >= pd.Timestamp(start_date)) & (
        df["Zulassung"] <= pd.Timestamp(end_date)
    )

if selected_municipalities:
    mask &= df["Gemeinden"].isin(selected_municipalities)

df_filtered = df[mask].copy()

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("OEM1 Emissions Investigation")
st.markdown(
    "Overview of vehicles affected by the T2 control unit emissions issue, "
    "prepared for OEM1 management."
)

# ------------------------------------------------------------------
# Tabs (single-file "pages")
# ------------------------------------------------------------------
tab_overview, tab_map, tab_table = st.tabs(["Overview", "Map", "Data Table"])

# ==========================================================
# TAB 1: OVERVIEW
# ==========================================================
with tab_overview:
    st.subheader("Trends")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Affected vehicles over time")
        st.caption("Based on vehicle registration date")

        by_month = (
            df_filtered.set_index("Zulassung")
            .resample("M")
            .size()
            .rename("Affected_Vehicles")
            .reset_index()
        )
        st.line_chart(
            by_month,
            x="Zulassung",
            y="Affected_Vehicles",
            color=PRIMARY_LIGHT_BLUE,
        )

    with col_right:
        st.markdown("#### Top 10 affected municipalities")

        top_municipalities = (
            df_filtered["Gemeinden"]
            .value_counts()
            .head(10)
            .rename_axis("Municipality")
            .reset_index(name="Affected_Vehicles")
        )
        st.bar_chart(
            top_municipalities,
            x="Municipality",
            y="Affected_Vehicles",
            color=PRIMARY_LIGHT_BLUE,
        )

    st.markdown("---")
    st.subheader("Key figures")

    total_affected = len(df_filtered)
    n_municipalities = df_filtered["Gemeinden"].nunique()
    n_type11 = (df_filtered["Vehicle_Type"] == "Type11").sum()
    n_type12 = (df_filtered["Vehicle_Type"] == "Type12").sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Affected vehicles", f"{total_affected:,}")
    col2.metric("Municipalities affected", f"{n_municipalities:,}")
    col3.metric("Type11", f"{n_type11:,}")
    col4.metric("Type12", f"{n_type12:,}")

    st.markdown("---")
    st.subheader("Geographic preview")
    st.caption(
        "Affected vehicles by registered municipality. "
        "See the Map tab for the full interactive view."
    )

    map_data = df_filtered.dropna(subset=["Breitengrad", "Laengengrad"])[
        ["Breitengrad", "Laengengrad"]
    ].rename(columns={"Breitengrad": "lat", "Laengengrad": "lon"})

    st.map(map_data, color=PRIMARY_LIGHT_BLUE, size=10)

    st.markdown("---")
    st.caption(
        "Use the filters in the sidebar to narrow the analysis by vehicle "
        "type, registration date, or municipality. See the Map and Data "
        "Table tabs for further detail."
    )

# ==========================================================
# TAB 2: MAP (placeholder for now)
# ==========================================================
with tab_map:
    st.subheader("Geographic distribution")
    st.info("Map view — to be implemented next.")

# ==========================================================
# TAB 3: DATA TABLE (placeholder for now)
# ==========================================================
with tab_table:
    st.subheader("Full affected vehicle dataset")
    st.info("Data table view — to be implemented next.")