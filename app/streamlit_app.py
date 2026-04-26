"""
streamlit_app.py
Interactive labor forecasting dashboard for the auto auction facility.
Run with:  streamlit run app/streamlit_app.py
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from forecast.forecast_engine import (
    get_week_forecast,
    get_wow_variance,
    get_monthly_trend,
    get_anomalies,
    build_forecast_context,
    forecast_staff_for_volume,
)
from forecast.ai_summary import generate_summary

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auction Labor Forecast",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚗 Auction Labor Forecast")
st.sidebar.markdown("---")

api_key = st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    help="Get a free key at console.anthropic.com",
)

selected_date = st.sidebar.date_input(
    "Forecast Start Date",
    value=date(2024, 4, 1),
    min_value=date(2024, 1, 1),
    max_value=date(2024, 12, 25),
)

st.sidebar.markdown("---")
st.sidebar.markdown("**What-If Volume Override**")
override_volume = st.sidebar.number_input(
    "Enter custom volume (0 = use forecast)",
    min_value=0, max_value=600, value=0, step=10,
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "📁 [View on GitHub](https://github.com) | "
    "Built with Python · SQL · Claude API"
)

# ── Main title ────────────────────────────────────────────────────────────────
st.title("🚗 Auto Auction Labor Forecasting")
st.caption(f"Forecast week starting {selected_date.strftime('%B %d, %Y')}")

# ── Load data ─────────────────────────────────────────────────────────────────
# Auto-generate database if it doesn't exist
db_path = os.path.join(os.path.dirname(__file__), '..', 'auction_data.db')
if not os.path.exists(db_path):
    from data.generate_data import generate_year, load_to_sqlite
    records = generate_year(2024)
    load_to_sqlite(records, db_path)
if not os.path.exists(db_path):
    from data.generate_data import generate_year, load_to_sqlite
    records = generate_year(2024)
    load_to_sqlite(records, db_path)

try:
    week_df    = get_week_forecast(selected_date)
    wow_df     = get_wow_variance(selected_date, weeks=8)
    monthly_df = get_monthly_trend()
    anomaly_df = get_anomalies()
    ctx        = build_forecast_context(selected_date)
except FileNotFoundError:
    st.error("Database not found. Run `python data/generate_data.py` first.")
    st.stop()
# ── KPI row ───────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

today_row = week_df.iloc[0] if not week_df.empty else None

with col1:
    vol = int(today_row["planned_volume"]) if today_row is not None else 0
    st.metric("📦 Today's Volume", f"{vol:,} cars")

with col2:
    staff = int(today_row["total_planned_staff"]) if today_row is not None else 0
    st.metric("👷 Staff Needed Today", f"{staff}")

with col3:
    sale = "✅ Yes" if (today_row is not None and today_row["is_sale_day"]) else "❌ No"
    st.metric("🔨 Sale Day", sale)

with col4:
    var = ctx["variance_staff"]
    delta_color = "inverse" if var < 0 else "normal"
    st.metric("📊 Last Actual Variance", f"{var:+d} staff", delta_color=delta_color)

st.markdown("---")

# ── What-If panel ─────────────────────────────────────────────────────────────
if override_volume > 0:
    st.subheader("🔧 What-If Staffing Calculator")
    dow_name  = selected_date.strftime("%A")
    is_sale   = dow_name in {"Tuesday", "Wednesday"}
    breakdown = forecast_staff_for_volume(override_volume, is_sale)

    wif_cols = st.columns(len(breakdown))
    labels = {
        "check_in": "Check-In", "detailing": "Detailing",
        "transport": "Transport", "title_admin": "Title/Admin",
        "lane_support": "Lane Support", "total": "TOTAL",
    }
    for i, (role, count) in enumerate(breakdown.items()):
        with wif_cols[i]:
            st.metric(labels.get(role, role), count)
    st.caption(f"Custom volume: {override_volume} cars on a {dow_name}")
    st.markdown("---")

# ── Week forecast table + chart ───────────────────────────────────────────────
st.subheader("📅 7-Day Staffing Forecast")

tab1, tab2 = st.tabs(["Table", "Chart"])

with tab1:
    display_df = week_df.copy()
    display_df["is_sale_day"] = display_df["is_sale_day"].map({1: "✅", 0: ""})
    display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    fig = go.Figure()
    fig.add_bar(
        x=week_df["day_of_week"],
        y=week_df["planned_volume"],
        name="Planned Volume",
        yaxis="y2",
        marker_color="rgba(99,110,250,0.3)",
    )
    fig.add_scatter(
        x=week_df["day_of_week"],
        y=week_df["total_planned_staff"],
        name="Staff Needed",
        mode="lines+markers",
        line=dict(color="#00cc96", width=3),
        marker=dict(size=8),
    )
    fig.update_layout(
        yaxis=dict(title="Staff Headcount"),
        yaxis2=dict(title="Vehicle Volume", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        height=380,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Monthly trend ─────────────────────────────────────────────────────────────
st.subheader("📈 Monthly Volume & Staffing Trend")

fig2 = px.bar(
    monthly_df, x="month_name", y="total_volume",
    color="avg_daily_staff",
    color_continuous_scale="Blues",
    labels={"total_volume": "Total Vehicles", "avg_daily_staff": "Avg Daily Staff"},
    height=320,
)
fig2.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── WoW variance ─────────────────────────────────────────────────────────────
st.subheader("📊 Week-over-Week Staffing Variance")

fig3 = px.bar(
    wow_df, x="week", y="variance_pct",
    color="variance_pct",
    color_continuous_scale=["#ef553b", "#f0f0f0", "#00cc96"],
    color_continuous_midpoint=0,
    labels={"variance_pct": "Variance %", "week": "Week"},
    height=300,
)
fig3.add_hline(y=0, line_dash="dash", line_color="gray")
fig3.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ── Anomaly table ─────────────────────────────────────────────────────────────
with st.expander("⚠️ High-Variance Days (anomaly log)", expanded=False):
    if anomaly_df.empty:
        st.success("No anomalies detected.")
    else:
        styled = anomaly_df.copy()
        styled.columns = [c.replace("_", " ").title() for c in styled.columns]
        st.dataframe(styled, use_container_width=True, hide_index=True)

st.markdown("---")

# ── AI Summary ────────────────────────────────────────────────────────────────
st.subheader("🤖 AI Supervisor Briefing")

if st.button("Generate Staffing Summary", type="primary"):
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar to generate summaries.")
    else:
        with st.spinner("Generating briefing..."):
            summary = generate_summary(ctx, api_key=api_key)
        st.info(summary)
        st.caption(
            f"Generated for {ctx['date']} · {ctx['day_of_week']} · "
            f"{'Sale Day' if ctx['is_sale_day'] else 'Non-Sale Day'}"
        )
else:
    st.caption("Enter your API key in the sidebar, then click the button above.")
