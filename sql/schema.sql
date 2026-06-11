-- ==========================================
-- Database Schema for Sales & Revenue MIS System
-- Target Dialect: PostgreSQL / SQL Server / SQLite compatible DDL
-- Design Pattern: Star Schema (1 Fact Table, 2 Dimension Tables, 1 Target Table)
-- ==========================================

-- 1. Dimension Table: Products
CREATE TABLE dim_products (
    product_key SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL UNIQUE,
    product_category VARCHAR(100) NOT NULL
);

-- 2. Dimension Table: Regions
CREATE TABLE dim_regions (
    region_key SERIAL PRIMARY KEY,
    region_name VARCHAR(50) NOT NULL UNIQUE
);

-- 3. Target Table: Monthly Sales Targets
CREATE TABLE dim_targets (
    target_key SERIAL PRIMARY KEY,
    target_month DATE NOT NULL,
    region_name VARCHAR(50) NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    target_revenue NUMERIC(15, 2) NOT NULL,
    CONSTRAINT uq_target UNIQUE (target_month, region_name, product_category)
);

-- 4. Fact Table: Sales Transactions
CREATE TABLE fact_sales (
    sales_key SERIAL PRIMARY KEY,
    transaction_id INT NOT NULL UNIQUE,
    sale_date DATE NOT NULL,
    product_key INT NOT NULL,
    region_key INT NOT NULL,
    units_sold INT NOT NULL CHECK (units_sold >= 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    revenue NUMERIC(15, 2) NOT NULL,
    cost NUMERIC(15, 2) NOT NULL,
    profit NUMERIC(15, 2) NOT NULL,
    profit_margin NUMERIC(5, 4) NOT NULL,
    FOREIGN KEY (product_key) REFERENCES dim_products (product_key),
    FOREIGN KEY (region_key) REFERENCES dim_regions (region_key)
);

-- Indexing for Query Performance Optimization (BI Ready)
CREATE INDEX idx_fact_sales_date ON fact_sales (sale_date);
CREATE INDEX idx_fact_sales_product ON fact_sales (product_key);
CREATE INDEX idx_fact_sales_region ON fact_sales (region_key);
CREATE INDEX idx_dim_targets_lookup ON dim_targets (target_month, region_name, product_category);
