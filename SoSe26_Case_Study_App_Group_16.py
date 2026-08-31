"""
SoSe26 Case Study - Group 16 - OEM1 Emissions Investigation

Streamlit web application presenting the results of the T2 control unit
emissions investigation to OEM1 management: affected vehicle counts,
geographic distribution, and a full data table.

Run with on the terminal:
    <streamlit run SoSe26_Case_Study_App_Group_16.py>
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import base64
from pathlib import Path

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="OEM1 Emissions Investigation",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Static assets folder
# ------------------------------------------------------------------
WWW_DIR = Path(__file__).parent / "www"
LOGO_PATH = WWW_DIR / "logo" / "logo.png"
FONT_REGULAR_PATH = WWW_DIR / "fonts" / "SourceSans3-Regular.ttf"
FONT_BOLD_PATH = WWW_DIR / "fonts" / "SourceSans3-Bold.ttf"

PRIMARY_LIGHT_BLUE = "#5DADE2"
PRIMARY_LIGHT_BLUE_BG = "#EAF4FB"


def _load_font_base64(path: Path) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return None


_font_regular_b64 = _load_font_base64(FONT_REGULAR_PATH)
_font_bold_b64 = _load_font_base64(FONT_BOLD_PATH)

_font_css = f"""
@font-face {{
    font-family: 'Source Sans Pro';
    src: url(data:font/ttf;base64,{_font_regular_b64}) format('truetype');
    font-weight: 400;
}}
"""
if _font_bold_b64:
    _font_css += f"""
    @font-face {{
        font-family: 'Source Sans Pro';
        src: url(data:font/ttf;base64,{_font_bold_b64}) format('truetype');
        font-weight: 700;
    }}
    """


st.markdown(
    f"""
    <style>
        {_font_css}

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
# ------------------------------------------------------------------
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        # Fallback while the logo file isn't placed in www/ yet.
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
    "Overview of vehicles affected by the T2 control unit emissions issue. "
)

# ------------------------------------------------------------------
# Tabs (single-file "pages")
# ------------------------------------------------------------------
tab_overview, tab_map, tab_table = st.tabs(["Overview", "Map", "Dataset"])

# ==========================================================
# TAB 1: OVERVIEW
# ==========================================================
with tab_overview:
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
    st.caption(
        "Use the filters in the sidebar to narrow the analysis by vehicle "
        "type, registration date, or municipality. See the Map and Data "
        "Table tabs for further detail."
    )

# ==========================================================
# TAB 2: MAP
# ==========================================================
with tab_map:
    st.subheader("Geographic distribution")
    st.caption(
        "Each point represents a municipality. Dot size and colour "
        "intensity scale with the number of affected vehicles registered "
        "there — larger, darker points indicate higher concentration."
    )

    muni_agg = (
        df_filtered.dropna(subset=["Breitengrad", "Laengengrad"])
        .groupby(["Gemeinden", "Breitengrad", "Laengengrad"], as_index=False)
        .size()
        .rename(columns={"size": "Affected_Vehicles"})
    )

    if muni_agg.empty:
        st.warning("No data to display for the current filter selection.")
    else:
        max_count = muni_agg["Affected_Vehicles"].max()

        # Radius: square-root scale so *area* (not raw radius) is
        # proportional to vehicle count -- this avoids the largest
        # municipalities visually overwhelming the map.
        MIN_RADIUS = 300
        MAX_RADIUS = 6000
        muni_agg["radius"] = MIN_RADIUS + (
            (muni_agg["Affected_Vehicles"] / max_count) ** 0.5
        ) * (MAX_RADIUS - MIN_RADIUS)

        # Colour: light blue (low density) -> dark navy (high density)
        LIGHT = (93, 173, 226)   # matches the app's light-blue accent
        DARK = (21, 64, 96)

        def density_color(count: int) -> list:
            ratio = count / max_count
            r = int(LIGHT[0] + (DARK[0] - LIGHT[0]) * ratio)
            g = int(LIGHT[1] + (DARK[1] - LIGHT[1]) * ratio)
            b = int(LIGHT[2] + (DARK[2] - LIGHT[2]) * ratio)
            return [r, g, b, 180]

        muni_agg["color"] = muni_agg["Affected_Vehicles"].apply(density_color)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=muni_agg,
            get_position=["Laengengrad", "Breitengrad"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.7,
            stroked=False,
        )

        view_state = pdk.ViewState(
            latitude=muni_agg["Breitengrad"].mean(),
            longitude=muni_agg["Laengengrad"].mean(),
            zoom=5,
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip={"text": "{Gemeinden}\n{Affected_Vehicles} affected vehicles"},
            )
        )

        st.markdown("---")
        st.markdown("#### Top 10 municipalities in current view")
        st.dataframe(
            muni_agg.sort_values("Affected_Vehicles", ascending=False)
            .head(10)[["Gemeinden", "Affected_Vehicles"]]
            .reset_index(drop=True),
            use_container_width=True,
        )

# ==========================================================
# TAB 3: DATASET
# ==========================================================
with tab_table:
    st.subheader("Dataset")
    st.caption(
        f"{len(df_filtered):,} rows match the current sidebar filters. "
        "Use the column filters below to narrow it further."
    )

    with st.expander("Filter columns", expanded=False):
        col_filter_mask = pd.Series(True, index=df_filtered.index)

        for col in df_filtered.columns:
            series = df_filtered[col]

            if pd.api.types.is_datetime64_any_dtype(series):
                col_min, col_max = series.min(), series.max()
                if pd.isna(col_min) or pd.isna(col_max):
                    continue
                date_val = st.date_input(
                    col,
                    value=(col_min, col_max),
                    min_value=col_min,
                    max_value=col_max,
                    key=f"filter_{col}",
                )
                if isinstance(date_val, tuple) and len(date_val) == 2:
                    start, end = date_val
                    col_filter_mask &= (series >= pd.Timestamp(start)) & (
                        series <= pd.Timestamp(end)
                    )

            elif pd.api.types.is_numeric_dtype(series):
                col_min = float(series.min())
                col_max = float(series.max())
                if col_min == col_max:
                    continue
                selected_range = st.slider(
                    col,
                    min_value=col_min,
                    max_value=col_max,
                    value=(col_min, col_max),
                    key=f"filter_{col}",
                )
                col_filter_mask &= series.between(*selected_range)

            else:
                n_unique = series.nunique()
                if n_unique <= 100:
                    # Low-cardinality text column (e.g. Vehicle_Type):
                    # exact-value multiselect.
                    options = sorted(series.dropna().unique().tolist())
                    selected = st.multiselect(
                        col,
                        options=options,
                        default=[],
                        key=f"filter_{col}",
                        help="Leave empty to include all values.",
                    )
                    if selected:
                        col_filter_mask &= series.isin(selected)
                else:
                    # High-cardinality text column (e.g. ID_Motor, Gemeinden):
                    # a dropdown of thousands of options isn't practical,
                    # so filter by substring instead.
                    text_val = st.text_input(
                        f"{col} contains",
                        value="",
                        key=f"filter_{col}",
                    )
                    if text_val:
                        col_filter_mask &= (
                            series.astype(str).str.contains(text_val, case=False, na=False)
                        )

    table_df = df_filtered[col_filter_mask]

    st.markdown(f"**Showing {len(table_df):,} of {len(df_filtered):,} rows**")
    st.dataframe(table_df, use_container_width=True, height=500)

    csv_bytes = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered data as CSV",
        data=csv_bytes,
        file_name="filtered_affected_vehicles.csv",
        mime="text/csv",
    )