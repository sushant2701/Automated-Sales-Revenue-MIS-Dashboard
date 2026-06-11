import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sqlite3

# Import backend pipelines
from src.etl_pipeline import clean_sales_data, apply_transformations, generate_key_metrics, style_excel_sheet
from src.db_loader import run_db_pipeline
from src.alert_reporter import query_db_metrics, build_report_markdown

# Initialize session state for tracking runs
if "pipeline_run" not in st.session_state:
    st.session_state["pipeline_run"] = False

st.title("Sales & Revenue MIS Dashboard")
st.write("Deduplicate raw logs, load SQL schemas, and view analytics by uploading files below.")

st.write("---")

# 1. Main Page File Uploaders (Horizontal Layout)
st.subheader("Step 1: Upload Raw Datasets")
col_up1, col_up2 = st.columns(2)
with col_up1:
    sales_upload = st.file_uploader("Upload raw Sales CSV", type="csv")
with col_up2:
    targets_upload = st.file_uploader("Upload raw Targets CSV", type="csv")

# Pipeline Trigger buttons
st.subheader("Step 2: Process Data")
col_btn1, col_btn2 = st.columns(2)

def run_my_pipeline(sales_file, targets_file):
    # Save files to data/raw
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/raw_sales_data.csv", "wb") as f:
        f.write(sales_file.getbuffer())
    with open("data/raw/raw_targets_data.csv", "wb") as f:
        f.write(targets_file.getbuffer())
        
    # Execute Pandas cleaning and computations
    raw_sales = pd.read_csv("data/raw/raw_sales_data.csv")
    raw_targets = pd.read_csv("data/raw/raw_targets_data.csv")
    
    clean_sales = clean_sales_data(raw_sales)
    trans_sales = apply_transformations(clean_sales)
    metrics = generate_key_metrics(trans_sales, raw_targets)
    
    # Save outputs
    os.makedirs("data/cleaned", exist_ok=True)
    trans_sales.to_csv("data/cleaned/cleaned_sales_data.csv", index=False)
    metrics.to_csv("data/cleaned/cleaned_metrics_data.csv", index=False)
    
    # Write styled Excel sheets
    with pd.ExcelWriter("data/cleaned/cleaned_mis_snapshot.xlsx") as writer:
        trans_sales.to_excel(writer, sheet_name="Cleaned_Sales", index=False)
        metrics.to_excel(writer, sheet_name="Key_Metrics", index=False)
        style_excel_sheet(writer.sheets['Cleaned_Sales'])
        style_excel_sheet(writer.sheets['Key_Metrics'], is_metrics=True)
        
    # Run DB schema creation and SQLAlchemy load
    run_db_pipeline()
    
    # Generate weekly report
    db_metrics = query_db_metrics("sales_mis.db")
    report_md = build_report_markdown(db_metrics)
    os.makedirs("docs/reports", exist_ok=True)
    with open("docs/reports/weekly_sales_report.md", "w") as f:
        f.write(report_md)

with col_btn1:
    if st.button("Run ETL & Create Insights", use_container_width=True):
        if sales_upload and targets_upload:
            with st.spinner("Processing data..."):
                run_my_pipeline(sales_upload, targets_upload)
                st.session_state["pipeline_run"] = True
                st.success("Pipeline executed! Insights generated below.")
        else:
            st.error("Please upload both files first!")

with col_btn2:
    if st.button("Load Mock Sample Data", use_container_width=True):
        with st.spinner("Loading dummy datasets..."):
            os.system("python src/data_generator.py")
            os.system("python src/etl_pipeline.py")
            os.system("python src/db_loader.py")
            os.system("python src/alert_reporter.py")
            st.session_state["pipeline_run"] = True
            st.success("Mock sample data loaded! Insights generated below.")

st.write("---")

# 2. Main Page Dashboard (Rendered only if pipeline run occurred or DB exists)
if st.session_state["pipeline_run"] or os.path.exists("sales_mis.db"):
    st.subheader("Step 3: Executive Insights")
    
    conn = sqlite3.connect("sales_mis.db")
    
    # Fetch aggregates
    stats_df = pd.read_sql_query("SELECT SUM(revenue) as rev, SUM(profit) as profit FROM fact_sales;", conn)
    target_df = pd.read_sql_query("SELECT SUM(target_revenue) as target FROM dim_targets;", conn)
    
    total_rev = stats_df["rev"].iloc[0] or 0.0
    total_prof = stats_df["profit"].iloc[0] or 0.0
    target_rev = target_df["target"].iloc[0] or 1.0
    
    # Render metric cards
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(label="Total Revenue", value=f"${total_rev:,.2f}")
    col_m2.metric(label="Total Profit", value=f"${total_prof:,.2f}")
    col_m3.metric(label="Target Achievement Rate", value=f"{total_rev / target_rev * 100:.1f}%")
    
    # Page switcher tabs
    tab_charts, tab_table, tab_download = st.tabs(["Overview Charts", "Cleaned Table", "Download Center"])
    
    with tab_charts:
        # 1. Line Chart
        monthly_sales = pd.read_sql_query("""
            SELECT strftime('%Y-%m', sale_date) as Month, SUM(revenue) as Revenue 
            FROM fact_sales GROUP BY Month;
        """, conn)
        fig_line = px.line(monthly_sales, x="Month", y="Revenue", title="Monthly Revenue Trend ($)")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # 2. Regional Sales Bar Chart
        regional_sales = pd.read_sql_query("""
            SELECT r.region_name as Region, SUM(f.revenue) as Revenue
            FROM fact_sales f JOIN dim_regions r ON f.region_key = r.region_key
            GROUP BY Region;
        """, conn)
        fig_bar = px.bar(regional_sales, x="Region", y="Revenue", title="Revenue by Region ($)")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with tab_table:
        all_data = pd.read_sql_query("""
            SELECT f.transaction_id, f.sale_date, r.region_name, p.product_name, f.units_sold, f.revenue
            FROM fact_sales f
            JOIN dim_products p ON f.product_key = p.product_key
            JOIN dim_regions r ON f.region_key = r.region_key
            ORDER BY f.sale_date DESC;
        """, conn)
        st.write(f"Total Transactions Cleaned: {len(all_data)}")
        st.dataframe(all_data, use_container_width=True)
        
    with tab_download:
        st.write("Click below to download the cleaned snapshot files:")
        
        down_col1, down_col2, down_col3 = st.columns(3)
        
        with down_col1:
            if os.path.exists("data/cleaned/cleaned_mis_snapshot.xlsx"):
                with open("data/cleaned/cleaned_mis_snapshot.xlsx", "rb") as f:
                    st.download_button(
                        label="Download Excel Snapshot",
                        data=f,
                        file_name="cleaned_mis_snapshot.xlsx",
                        use_container_width=True
                    )
            else:
                st.write("Excel workbook not ready.")
                
        with down_col2:
            if os.path.exists("sales_mis.db"):
                with open("sales_mis.db", "rb") as f:
                    st.download_button(
                        label="Download SQLite DB File",
                        data=f,
                        file_name="sales_mis.db",
                        use_container_width=True
                    )
            else:
                st.write("SQL database not ready.")
                
        with down_col3:
            if os.path.exists("docs/reports/weekly_sales_report.md"):
                with open("docs/reports/weekly_sales_report.md", "rb") as f:
                    st.download_button(
                        label="Download Markdown Report",
                        data=f,
                        file_name="weekly_sales_report.md",
                        use_container_width=True
                    )
            else:
                st.write("Report draft not ready.")
                
    conn.close()
else:
    st.info("💡 Please upload your CSVs or click 'Load Mock Sample Data' above to start generating insights.")
