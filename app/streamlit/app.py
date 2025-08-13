import streamlit as st
import polars as pl
import plotly.express as px

st.set_page_config(page_title="Flight Reliability", layout="wide")
st.title("Flight Reliability MVP")
st.caption("Canada + U.S. (historical sample) • Live layer coming soon")

# ---------- Load data ----------
@st.cache_data
def load_data(path: str) -> pl.DataFrame:
    df = pl.read_csv(path, try_parse_dates=True)
    # Parse HHMM times into minutes since midnight for easy bucketing
    def hhmm_to_minutes(s):
        # s is like 0800, 1515; handle missing safely
        return (s // 100) * 60 + (s % 100)

    df = df.with_columns([
        pl.col("CRSDepTime").cast(pl.Int64).map_elements(hhmm_to_minutes).alias("CRSDepMin"),
        pl.col("DepTime").cast(pl.Int64).map_elements(hhmm_to_minutes).alias("DepMin"),
        pl.col("CRSArrTime").cast(pl.Int64).map_elements(hhmm_to_minutes).alias("CRSArrMin"),
        pl.col("ArrTime").cast(pl.Int64).map_elements(hhmm_to_minutes).alias("ArrMin"),
        (pl.col("ArrDelayMinutes") <= 15).cast(pl.Int8).alias("OnTime"),
        pl.col("Cancelled").cast(pl.Int8).alias("CancelledFlag"),
    ])
    # Hour buckets by scheduled departure time
    df = df.with_columns((pl.col("CRSDepMin") // 60).alias("DepHour"))
    return df

DATA_PATH = "data/samples/flights_sample.csv"
df = load_data(DATA_PATH)

# ---------- Sidebar filters ----------
st.sidebar.header("Search / Filters")

modes = {
    "Airport (Origin)": "airport",
    "Route (Origin → Dest)": "route",
    "Airline at Airport": "airline_at_airport",
    "Flight Number": "flight",
}
mode_label = st.sidebar.selectbox("View", list(modes.keys()))
mode = modes[mode_label]

# Build filter widgets based on mode
airports = sorted(set(df["Origin"].to_list()) | set(df["Dest"].to_list()))
airlines = sorted(df["Operating_Airline"].unique().to_list())
flight_ids = sorted((df["Operating_Airline"] + df["Flight_Number_Operating_Airline"].cast(pl.Utf8)).unique().to_list())
orig = st.sidebar.selectbox("Origin", airports, index=airports.index("JFK") if "JFK" in airports else 0)
dest = st.sidebar.selectbox("Destination", airports, index=airports.index("LAX") if "LAX" in airports else 0)
carrier = st.sidebar.selectbox("Airline", airlines, index=0)
flight = st.sidebar.selectbox("Flight (Carrier+Number)", flight_ids, index=0)
period = st.sidebar.selectbox("Period", ["All (sample)"], index=0)

# ---------- Filter data based on mode ----------
def filter_df(df: pl.DataFrame) -> pl.DataFrame:
    if mode == "airport":
        return df.filter(pl.col("Origin") == orig)
    if mode == "route":
        return df.filter((pl.col("Origin") == orig) & (pl.col("Dest") == dest))
    if mode == "airline_at_airport":
        return df.filter((pl.col("Origin") == orig) & (pl.col("Operating_Airline") == carrier))
    if mode == "flight":
        # flight string is like "AA100"
        f_car = flight[:2]
        f_no = flight[2:]
        return df.filter((pl.col("Operating_Airline") == f_car) & (pl.col("Flight_Number_Operating_Airline").cast(pl.Utf8) == f_no))
    return df

fdf = filter_df(df)

# ---------- Compute metrics ----------
def compute_metrics(fdf: pl.DataFrame) -> dict:
    n = fdf.height
    if n == 0:
        return {"n": 0, "on_time_pct": None, "avg_delay": None, "cancel_rate": None}
    on_time = fdf["OnTime"].sum()
    cancels = fdf["CancelledFlag"].sum()
    avg_delay = fdf["ArrDelayMinutes"].mean()
    return {
        "n": int(n),
        "on_time_pct": round(on_time / n * 100, 1),
        "avg_delay": round(float(avg_delay), 1) if avg_delay is not None else None,
        "cancel_rate": round(cancels / n * 100, 1)
    }

metrics = compute_metrics(fdf)

# ---------- Header / selection summary ----------
with st.container():
    if mode == "airport":
        st.subheader(f"Origin Airport: {orig}")
    elif mode == "route":
        st.subheader(f"Route: {orig} → {dest}")
    elif mode == "airline_at_airport":
        st.subheader(f"Airline at Airport: {carrier} @ {orig}")
    elif mode == "flight":
        st.subheader(f"Flight: {flight}")

# ---------- KPI cards ----------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Flights (sample)", metrics["n"])
kpi2.metric("On-Time % (≤15m)", "-" if metrics["on_time_pct"] is None else f'{metrics["on_time_pct"]}%')
kpi3.metric("Avg Arrival Delay (min)", "-" if metrics["avg_delay"] is None else metrics["avg_delay"])
kpi4.metric("Cancel Rate", "-" if metrics["cancel_rate"] is None else f'{metrics["cancel_rate"]}%')

# ---------- Charts ----------
if fdf.height > 0:
    # Best/Worst by DepHour
    hour_stats = (
        fdf.group_by("DepHour")
           .agg([
               pl.len().alias("flights_n"),
               pl.mean("OnTime").alias("on_time_rate"),
               pl.mean("ArrDelayMinutes").alias("avg_arr_delay")
           ])
           .with_columns([
               (pl.col("on_time_rate") * 100).round(1).alias("on_time_pct")
           ])
           .sort("DepHour")
    )

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(hour_stats.to_pandas(), x="DepHour", y="on_time_pct",
                     title="On-Time % by Scheduled Departure Hour", labels={"DepHour":"Hour (0–23)","on_time_pct":"On-Time %"})
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.bar(hour_stats.to_pandas(), x="DepHour", y="avg_arr_delay",
                      title="Average Arrival Delay (min) by Hour", labels={"DepHour":"Hour (0–23)","avg_arr_delay":"Avg Delay (min)"})
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.dataframe(fdf.select([
        "FlightDate","Operating_Airline","Flight_Number_Operating_Airline",
        "Origin","Dest","CRSDepTime","DepTime","CRSArrTime","ArrTime",
        "ArrDelayMinutes","Cancelled"
    ]).sort(["FlightDate","Operating_Airline","Flight_Number_Operating_Airline"]).to_pandas())
else:
    st.info("No flights match your selection in this sample. Try a different filter.")
