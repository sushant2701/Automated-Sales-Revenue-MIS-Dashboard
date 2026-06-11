import os
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

def query_db_metrics(db_path="sales_mis.db"):
    """
    Connects to the SQLite database and executes analytical queries
    to gather data for the executive performance summary report.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database '{db_path}' not found. Please run the DB loader script first.")
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Total Financial Performance (Aggregated)
    cursor.execute("""
        SELECT 
            SUM(revenue) as total_rev,
            SUM(cost) as total_cost,
            SUM(profit) as total_profit,
            AVG(profit_margin) * 100 as avg_margin
        FROM fact_sales;
    """)
    totals = cursor.fetchone()
    
    # 2. Latest Month Performance
    cursor.execute("SELECT MAX(sale_date) FROM fact_sales;")
    max_date_str = cursor.fetchone()[0]
    latest_month = datetime.strptime(max_date_str, "%Y-%m-%d").strftime("%Y-%m") if max_date_str else None
    
    latest_month_metrics = (0, 0, 0, 0)
    if latest_month:
        cursor.execute(f"""
            SELECT 
                SUM(revenue) as rev,
                SUM(cost) as cost,
                SUM(profit) as profit,
                (SUM(profit) / SUM(revenue)) * 100 as margin
            FROM fact_sales
            WHERE strftime('%Y-%m', sale_date) = '{latest_month}';
        """)
        latest_month_metrics = cursor.fetchone()
        
    # 3. Target Achievement & Variance by Region for latest month
    region_targets = []
    if latest_month:
        # Match target_month 'YYYY-MM-01' format
        target_month_date = f"{latest_month}-01"
        cursor.execute(f"""
            SELECT 
                r.region_name,
                SUM(f.revenue) as actual_revenue,
                t.target_revenue,
                (SUM(f.revenue) - t.target_revenue) as variance,
                (SUM(f.revenue) / t.target_revenue) * 100 as achievement_rate
            FROM fact_sales f
            JOIN dim_regions r ON f.region_key = r.region_key
            LEFT JOIN (
                SELECT region_name, SUM(target_revenue) as target_revenue
                FROM dim_targets
                WHERE target_month = '{target_month_date}'
                GROUP BY region_name
            ) t ON r.region_name = t.region_name
            WHERE strftime('%Y-%m', f.sale_date) = '{latest_month}'
            GROUP BY r.region_name, t.target_revenue;
        """)
        region_targets = cursor.fetchall()
        
    # 4. Product Category performance for latest month
    category_perf = []
    if latest_month:
        cursor.execute(f"""
            SELECT 
                p.product_category,
                SUM(f.units_sold) as total_units,
                SUM(f.revenue) as total_rev,
                (SUM(f.profit) / SUM(f.revenue)) * 100 as profit_margin
            FROM fact_sales f
            JOIN dim_products p ON f.product_key = p.product_key
            WHERE strftime('%Y-%m', f.sale_date) = '{latest_month}'
            GROUP BY p.product_category;
        """)
        category_perf = cursor.fetchall()
        
    conn.close()
    
    return {
        "latest_month": latest_month,
        "totals": totals,
        "latest_month_metrics": latest_month_metrics,
        "region_targets": region_targets,
        "category_perf": category_perf
    }

def build_report_markdown(metrics):
    """
    Compiles database metrics into a professional executive summary report.
    """
    latest_month = metrics["latest_month"]
    totals = metrics["totals"]
    month_metrics = metrics["latest_month_metrics"]
    region_targets = metrics["region_targets"]
    category_perf = metrics["category_perf"]
    
    month_name = datetime.strptime(latest_month, "%Y-%m").strftime("%B %Y") if latest_month else "N/A"
    
    # Header
    report = f"# Executive Performance Summary Report\n"
    report += f"**Report Period:** {month_name} (Snapshot)  \n"
    report += f"**Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n"
    
    report += "## 1. Executive Summary Table\n"
    report += "| Metric | Latest Month ({}) | Inception-to-Date (ITD) |\n".format(month_name)
    report += "| :--- | :---: | :---: |\n"
    report += f"| **Total Revenue** | ${month_metrics[0]:,.2f} | ${totals[0]:,.2f} |\n"
    report += f"| **Total Cost** | ${month_metrics[1]:,.2f} | ${totals[1]:,.2f} |\n"
    report += f"| **Net Profit** | ${month_metrics[2]:,.2f} | ${totals[2]:,.2f} |\n"
    report += f"| **Profit Margin** | {month_metrics[3]:.1f}% | {totals[3]:.1f}% |\n\n"
    
    # Region vs Target Table
    report += f"## 2. Regional Revenue vs Targets ({month_name})\n"
    report += "| Region | Actual Revenue | Target Revenue | Variance ($) | Achievement Rate |\n"
    report += "| :--- | :---: | :---: | :---: | :---: |\n"
    
    underperforming_regions = []
    
    for row in region_targets:
        region, actual, target, variance, achievement = row
        target = target if target else 0.0
        variance = variance if variance else actual
        achievement = achievement if achievement else 0.0
        
        ach_str = f"{achievement:.1f}%"
        if achievement < 90.0:
            ach_str = f"⚠️ **{achievement:.1f}%**"
            underperforming_regions.append((region, achievement))
            
        report += f"| {region} | ${actual:,.2f} | ${target:,.2f} | ${variance:+,.2f} | {ach_str} |\n"
        
    report += "\n"
    
    # Category Performance Table
    report += f"## 3. Product Category Breakdown ({month_name})\n"
    report += "| Product Category | Units Sold | Revenue | Profit Margin |\n"
    report += "| :--- | :---: | :---: | :---: |\n"
    for row in category_perf:
        cat, units, rev, margin = row
        report += f"| {cat} | {units:,} | ${rev:,.2f} | {margin:.1f}% |\n"
    report += "\n"
    
    # Alerts and Insights Section
    report += "## 4. Key Exceptions & Alert Flags\n"
    if underperforming_regions:
        for reg, ach in underperforming_regions:
            report += f"- 🔴 **ALERT:** The **{reg}** region has missed its sales target. Achieved only **{ach:.1f}%** of monthly budget.\n"
    else:
        report += "- 🟢 **STATUS:** All regions met or exceeded 90% of their target budgets.\n"
        
    # High-performing note
    best_ach = max(region_targets, key=lambda x: x[4] if x[4] is not None else 0) if region_targets else None
    if best_ach and best_ach[4] > 105.0:
        report += f"- 🏆 **HIGHLIGHT:** The **{best_ach[0]}** region is the top performer this month, reaching **{best_ach[4]:.1f}%** of its target.\n"
        
    report += "\n***\n*Note: This report is automatically generated and distributed by the BI pipeline. Please direct any queries to the data engineering team.*"
    
    return report

def send_mock_email(report_content, to_email="stakeholders@company.com"):
    """
    Simulates sending an email by printing the formatted headers and body.
    Supports a mock fallback or an active SMTP distribution channel.
    """
    print("\n" + "="*50)
    print("SIMULATED EMAIL BROADCAST OUTBOX")
    print("="*50)
    print(f"From:     mis-analytics@company.com")
    print(f"To:       {to_email}")
    print(f"Subject:  Automated Sales & Revenue MIS Summary - {datetime.now().strftime('%b %Y')}")
    print(f"Format:   Multipart/HTML (Markdown rendered)")
    print("-"*50)
    print(report_content)
    print("="*50 + "\n")
    
    # Write report file to docs/reports
    os.makedirs("docs/reports", exist_ok=True)
    report_file = "docs/reports/weekly_sales_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Report written successfully to: '{report_file}'")

def run_reporting_pipeline():
    """
    Orchestrator for extracting data, compiling reports, and broadcasting alerts.
    """
    print("Initiating Automated Reporting Workflow...")
    db_path = "sales_mis.db"
    
    try:
        metrics = query_db_metrics(db_path)
        report_md = build_report_markdown(metrics)
        send_mock_email(report_md)
        print("Reporting workflow executed successfully.")
    except Exception as e:
        print(f"Error during reporting workflow: {e}")

if __name__ == "__main__":
    run_reporting_pipeline()
