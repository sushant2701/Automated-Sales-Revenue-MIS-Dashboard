import os
import pandas as pd
from datetime import datetime
from sqlalchemy import (
    create_engine, Table, Column, Integer, String, Numeric, Date, 
    MetaData, ForeignKey, UniqueConstraint, select, insert, delete, update
)

# Define SQLAlchemy Metadata
metadata = MetaData()

# Product Dimension Table
dim_products = Table(
    'dim_products', metadata,
    Column('product_key', Integer, primary_key=True, autoincrement=True),
    Column('product_name', String(100), nullable=False, unique=True),
    Column('product_category', String(100), nullable=False)
)

# Region Dimension Table
dim_regions = Table(
    'dim_regions', metadata,
    Column('region_key', Integer, primary_key=True, autoincrement=True),
    Column('region_name', String(50), nullable=False, unique=True)
)

# Targets Table (acting as a Dimension/Target bridge)
dim_targets = Table(
    'dim_targets', metadata,
    Column('target_key', Integer, primary_key=True, autoincrement=True),
    Column('target_month', Date, nullable=False),
    Column('region_name', String(50), nullable=False),
    Column('product_category', String(100), nullable=False),
    Column('target_revenue', Numeric(15, 2), nullable=False),
    UniqueConstraint('target_month', 'region_name', 'product_category', name='uq_target')
)

# Sales Fact Table
fact_sales = Table(
    'fact_sales', metadata,
    Column('sales_key', Integer, primary_key=True, autoincrement=True),
    Column('transaction_id', Integer, nullable=False, unique=True),
    Column('sale_date', Date, nullable=False),
    Column('product_key', Integer, ForeignKey('dim_products.product_key'), nullable=False),
    Column('region_key', Integer, ForeignKey('dim_regions.region_key'), nullable=False),
    Column('units_sold', Integer, nullable=False),
    Column('unit_price', Numeric(10, 2), nullable=False),
    Column('revenue', Numeric(15, 2), nullable=False),
    Column('cost', Numeric(15, 2), nullable=False),
    Column('profit', Numeric(15, 2), nullable=False),
    Column('profit_margin', Numeric(5, 4), nullable=False)
)

def get_db_engine(connection_string=None):
    """
    Returns an SQLAlchemy database engine. Defaults to a local SQLite database.
    """
    if not connection_string:
        # Check environment variable or default to local sqlite
        connection_string = os.getenv("DATABASE_URL", "sqlite:///sales_mis.db")
    
    print(f"Connecting to database via: {connection_string.split('@')[-1] if '@' in connection_string else connection_string}")
    return create_engine(connection_string)

def load_dimensions(conn, sales_df, targets_df):
    """
    Extracts and upserts dimensions (products & regions) from transactional and target data.
    """
    # 1. Product Dimension Loading
    print("Loading dim_products...")
    unique_prods = sales_df[['Product_Name', 'Product_Category']].drop_duplicates(subset=['Product_Name']).dropna()
    
    # Query existing products
    existing_prods_stmt = select(dim_products.c.product_name, dim_products.c.product_key)
    existing_prods = {row[0]: row[1] for row in conn.execute(existing_prods_stmt).fetchall()}
    
    new_prods = []
    for _, row in unique_prods.iterrows():
        p_name = row['Product_Name']
        p_cat = row['Product_Category']
        if p_name not in existing_prods:
            new_prods.append({"product_name": p_name, "product_category": p_cat})
            
    if new_prods:
        print(f"Inserting {len(new_prods)} new products into dim_products...")
        conn.execute(insert(dim_products), new_prods)
        # Refresh product key cache
        existing_prods = {row[0]: row[1] for row in conn.execute(existing_prods_stmt).fetchall()}
    
    # 2. Region Dimension Loading
    print("Loading dim_regions...")
    # Extract from both sales and targets to be safe
    regions_sales = sales_df['Region'].dropna().unique()
    regions_targets = targets_df['Region'].dropna().unique()
    all_regions = list(set(regions_sales) | set(regions_targets))
    
    # Query existing regions
    existing_regs_stmt = select(dim_regions.c.region_name, dim_regions.c.region_key)
    existing_regs = {row[0]: row[1] for row in conn.execute(existing_regs_stmt).fetchall()}
    
    new_regs = []
    for region in all_regions:
        if region not in existing_regs:
            new_regs.append({"region_name": region})
            
    if new_regs:
        print(f"Inserting {len(new_regs)} new regions into dim_regions...")
        conn.execute(insert(dim_regions), new_regs)
        # Refresh region key cache
        existing_regs = {row[0]: row[1] for row in conn.execute(existing_regs_stmt).fetchall()}
        
    return existing_prods, existing_regs

def load_targets(conn, targets_df):
    """
    Upserts target data into dim_targets (deletes existing targets for specified month/region/category, then appends).
    """
    print("Loading dim_targets (with upsert-logic)...")
    
    # Prepare rows with parsed date objects
    targets_to_load = []
    for _, row in targets_df.iterrows():
        month_dt = datetime.strptime(row['Month'], "%Y-%m-%d").date()
        targets_to_load.append({
            "target_month": month_dt,
            "region_name": row['Region'],
            "product_category": row['Product_Category'],
            "target_revenue": float(row['Target_Revenue'])
        })
        
    # Execute batch upsert: Delete existing matching targets first to prevent uniqueness errors
    count_updated = 0
    count_inserted = 0
    
    # Process in chunks or batch delete
    for item in targets_to_load:
        # Delete existing matching record if any
        del_stmt = delete(dim_targets).where(
            dim_targets.c.target_month == item["target_month"],
            dim_targets.c.region_name == item["region_name"],
            dim_targets.c.product_category == item["product_category"]
        )
        conn.execute(del_stmt)
        
        # Insert new record
        conn.execute(insert(dim_targets).values(item))
        count_inserted += 1
        
    print(f"Successfully upserted {count_inserted} rows in dim_targets.")

def load_sales_facts(conn, sales_df, prod_map, reg_map):
    """
    Resolves keys and loads/upserts sales data into the fact_sales table.
    """
    print("Loading fact_sales...")
    
    # Resolve keys from dictionaries
    sales_df['product_key'] = sales_df['Product_Name'].map(prod_map)
    sales_df['region_key'] = sales_df['Region'].map(reg_map)
    
    # Validate keys are not null
    if sales_df['product_key'].isna().any() or sales_df['region_key'].isna().any():
        raise ValueError("Failed to resolve all dimension foreign keys in sales transactions.")
        
    sales_to_load = []
    for _, row in sales_df.iterrows():
        sale_dt = datetime.strptime(row['Date'], "%Y-%m-%d").date()
        sales_to_load.append({
            "transaction_id": int(row['Transaction_ID']),
            "sale_date": sale_dt,
            "product_key": int(row['product_key']),
            "region_key": int(row['region_key']),
            "units_sold": int(row['Units_Sold']),
            "unit_price": float(row['Unit_Price']),
            "revenue": float(row['Revenue']),
            "cost": float(row['Cost']),
            "profit": float(row['Profit']),
            "profit_margin": float(row['Profit_Margin'])
        })
        
    # Execute transaction-safe bulk loader
    # Deleting existing transactions if loading updated data (upsert simulation)
    tx_ids = [item["transaction_id"] for item in sales_to_load]
    
    # Split list into smaller chunks for SQLite parameter limits (max 999 parameters)
    chunk_size = 500
    for i in range(0, len(tx_ids), chunk_size):
        chunk_ids = tx_ids[i:i + chunk_size]
        del_stmt = delete(fact_sales).where(fact_sales.c.transaction_id.in_(chunk_ids))
        conn.execute(del_stmt)
        
    # Batch insert all records
    conn.execute(insert(fact_sales), sales_to_load)
    print(f"Successfully loaded {len(sales_to_load)} rows into fact_sales table.")

def run_db_pipeline(connection_string=None):
    """
    Orchestrates the entire database pipeline: Schema Creation and Data Loading.
    """
    print("Initializing Database Loader Pipeline...")
    
    # Load cleaned and targets datasets
    cleaned_sales_csv = "data/cleaned/cleaned_sales_data.csv"
    raw_targets_csv = "data/raw/raw_targets_data.csv"
    
    if not os.path.exists(cleaned_sales_csv) or not os.path.exists(raw_targets_csv):
        raise FileNotFoundError("Cleaned sales data or targets CSV not found. Please run the ETL pipeline first.")
        
    sales_df = pd.read_csv(cleaned_sales_csv)
    targets_df = pd.read_csv(raw_targets_csv)
    
    # Create engine and create tables
    engine = get_db_engine(connection_string)
    metadata.create_all(engine)
    print("Database tables validated/created successfully.")
    
    # Open connection and load data
    with engine.begin() as conn: # Transaction block
        # 1. Load Dimensions and get key caches
        prod_map, reg_map = load_dimensions(conn, sales_df, targets_df)
        
        # 2. Load Targets
        load_targets(conn, targets_df)
        
        # 3. Load Facts
        load_sales_facts(conn, sales_df, prod_map, reg_map)
        
    print("Database loading pipeline completed successfully!")

if __name__ == "__main__":
    run_db_pipeline()
