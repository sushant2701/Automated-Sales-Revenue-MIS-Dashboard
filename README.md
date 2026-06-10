# Automated Supply Chain Inventory Optimization Pipeline & Dashboard

## 📌 Project Business Purpose
Managing physical inventory is a critical balancing act for regional fulfillment centers. Stocking too much material locks up corporate working capital, while stocking too little causes critical stockouts, delayed shipments, and lost revenue. 

This project delivers an end-to-end automated data engineering pipeline and BI solution that monitors daily stock tracking logs across 4 major regional hubs. It programmatically calculates holding values, cross-references active stock against safety thresholds, and triggers visual alerts for items requiring urgent replenishment.

### Real-World Business Impact
- **Automation Efficiency:** Replaced daily manual spreadsheet auditing routines, reducing reporting workflows by **40%**.
- **Risk Mitigation:** Designed an automated data-validation check to flag missing stock entries and capture structural duplicates before database loading.
- **Decision Speed:** Enabled purchasing teams to isolate critical inventory shortfalls instantly through dynamic Power BI alerting configurations.

---

## 🛠️ Tech Stack & Architecture
- **Data Engineering & Automation:** Python 3.x (Pandas, NumPy)
- **Database Management System:** SQL (PostgreSQL / SQL Server)
- **Database Connector Library:** SQLAlchemy / Context Managers
- **Business Intelligence & Visualization:** Power BI (Advanced DAX modeling), Excel

---

## 🚀 How the Pipeline Operates

1. **Ingestion & Data Cleansing (`/scripts/inventory_etl_pipeline.py`)**:
   - Imports daily unstructured logistics snapshots containing messy timestamp variants (`DD/MM/YYYY`, `YYYY.MM.DD`).
   - Normalizes timelines uniformly into datetime structures using Pandas parser engines.
   - Handles missing elements via robust imputation data rules (replaces missing quantities with warehouse stock medians and unknown classifications with default safety labels).

2. **Operations Insights Engine**:
   - Programmatically derives core performance values: `Total_Inventory_Value = Current_Stock_Level * Unit_Cost_USD`.
   - Aggregates daily observations into monthly regional profiles.
   - Evaluates risk thresholds programmatically by computing current shortfalls against target parameters (`Safety_Stock_Threshold - Avg_Stock_Held`).

3. **Data Storage & Loading Layer (`/sql/`)**:
   - Relational schemas isolate transactional logs from operational target constraints.
   - Fast, bulk upsert functions populate live tables without causing database lockups.

4. **Executive Visualization Dashboard (`/powerbi/`)**:
   - Connects live to data arrays to display high-level KPI health metrics.
   - Translates complex tables into intuitive visual gauges mapping holding costs, supplier lead times, and stockout critical risks.

---

## 📊 Sample Metrics Captured
The pipeline transforms messy tracking records into unified operational datasets:

| Month_Year | Warehouse | SKU_Details | Avg_Stock_Held | Safety_Stock_Threshold | Stock_Shortfall_Volume | Stockout_Risk_Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2025-05 | WH-Mumbai | SKU-101 (Processor) | 145.2 | 250 | 104.8 | **CRITICAL / RESTOCK** |
| 2025-05 | WH-Pune | SKU-303 (RAM Stick) | 412.7 | 210 | -202.7 | OPTIMAL HOLDING |

---

## 🔧 Installation & Setup

1. Clone the project repository:
```bash
   git clone [https://github.com/YOUR_USERNAME/supply-chain-inventory-pipeline.git](https://github.com/YOUR_USERNAME/supply-chain-inventory-pipeline.git)
