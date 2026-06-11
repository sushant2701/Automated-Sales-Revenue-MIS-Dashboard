import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    # Fallback if Faker is not installed
    class Fake:
        def name(self):
            names = ["Acme Corp", "Globex Corporation", "Initech", "Umbrella Corp", "Stark Industries", 
                     "Wayne Enterprises", "Hooli", "Veer Retail", "Vertex Solutions", "Nexus Logistics"]
            return random.choice(names)
    fake = Fake()

def generate_messy_date(base_date):
    """
    Randomly generates a date string in one of several inconsistent formats,
    including standard YYYY-MM-DD, DD/MM/YYYY, Month DD, YYYY, or missing (NaN).
    """
    chance = random.random()
    if chance < 0.05:
        return np.nan
    elif chance < 0.35:
        # DD/MM/YYYY
        return base_date.strftime("%d/%m/%Y")
    elif chance < 0.65:
        # Month DD, YYYY
        return base_date.strftime("%B %d, %Y")
    elif chance < 0.85:
        # lowercase month dd, yyyy
        return base_date.strftime("%b %d, %Y").lower()
    else:
        # Standard YYYY-MM-DD
        return base_date.strftime("%Y-%m-%d")

def generate_messy_region(region):
    """
    Introduces inconsistency into Region categories.
    """
    chance = random.random()
    if chance < 0.10:
        return region[0]  # Abbreviation (N, S, E, W)
    elif chance < 0.20:
        return region.lower()  # lowercase (north, south, etc.)
    elif chance < 0.30:
        return region.upper()  # uppercase (NORTH, SOUTH, etc.)
    else:
        return region  # Standard (North, South, East, West)

def generate_messy_category(category):
    """
    Introduces whitespace and case inconsistencies.
    """
    chance = random.random()
    if chance < 0.15:
        return f" {category} "  # Leading and trailing spaces
    elif chance < 0.30:
        return category.lower()  # Lowercase
    else:
        return category

def generate_raw_sales_data(start_date, end_date, num_rows=1500):
    products = {
        "Electronics": [
            {"name": "Smart Phone", "price": 699.99},
            {"name": "Laptop", "price": 1199.99},
            {"name": "Wireless Headphones", "price": 149.99},
            {"name": "Smart Watch", "price": 249.99}
        ],
        "Furniture": [
            {"name": "Office Chair", "price": 189.99},
            {"name": "Dining Table", "price": 450.00},
            {"name": "Ergonomic Desk", "price": 299.99},
            {"name": "Sofa", "price": 799.99}
        ],
        "Office Supplies": [
            {"name": "Notebook", "price": 4.99},
            {"name": "Gel Pens (Pack of 10)", "price": 12.50},
            {"name": "Paper Shredder", "price": 89.99},
            {"name": "File Organizer", "price": 24.99}
        ]
    }
    
    regions = ["North", "South", "East", "West"]
    
    data = []
    
    # Generate transactions
    for i in range(num_rows):
        tx_id = 100000 + i
        
        # Random date in the 12-month range
        delta_days = (end_date - start_date).days
        random_days = random.randint(0, delta_days)
        sale_date = start_date + timedelta(days=random_days)
        
        # Category and Product
        category = random.choice(list(products.keys()))
        prod_info = random.choice(products[category])
        product_name = prod_info["name"]
        
        # Base price and units
        base_price = prod_info["price"]
        units_sold = random.randint(1, 15)
        
        # Messy variables
        units_val = units_sold
        price_val = base_price
        
        # Introduce missing / corrupted units & prices
        rand_val = random.random()
        if rand_val < 0.04:
            units_val = np.nan  # Missing Units
        elif rand_val < 0.06:
            units_val = -random.randint(1, 5)  # Negative Units (error)
            
        rand_val = random.random()
        if rand_val < 0.04:
            price_val = np.nan  # Missing Price
            
        # Calculate revenue, with occasional calculations discrepancies or NaNs
        if pd.isna(units_val) or pd.isna(price_val):
            revenue_val = np.nan
        else:
            revenue_val = units_val * price_val
            
        # Introduce revenue mismatch or NaN
        rand_val = random.random()
        if rand_val < 0.05:
            revenue_val = np.nan
        elif rand_val < 0.07:
            # Calculation mismatch
            revenue_val = revenue_val * 1.15 if revenue_val > 0 else 100.0
            
        # Customer Name
        customer = fake.name() if random.random() > 0.05 else np.nan
        
        # Formatted messy date
        date_str = generate_messy_date(sale_date)
        
        # Region
        region_str = generate_messy_region(random.choice(regions))
        if random.random() < 0.03:
            region_str = np.nan # Missing region
            
        # Category formatting
        cat_str = generate_messy_category(category)
        
        data.append({
            "Transaction_ID": tx_id,
            "Date": date_str,
            "Customer_Name": customer,
            "Product_Category": cat_str,
            "Product_Name": product_name,
            "Units_Sold": units_val,
            "Unit_Price": price_val,
            "Revenue": revenue_val,
            "Region": region_str
        })
        
    # Introduce duplicates
    # 1. Exact duplicates (entire rows duplicated)
    df = pd.DataFrame(data)
    dup_indices = df.sample(frac=0.03, random_state=42).index
    df_dups = df.loc[dup_indices]
    df = pd.concat([df, df_dups], ignore_index=True)
    
    # 2. Key duplicates with different content (same transaction ID, different product/amount)
    key_dup_indices = df.sample(frac=0.01, random_state=100).index
    for idx in key_dup_indices:
        # Mutate product/amount of the transaction ID
        row = df.loc[idx].copy()
        row["Product_Name"] = "Mutated Product"
        row["Revenue"] = 999.99
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        
    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df

def generate_targets_data(start_date, end_date):
    """
    Generates target revenue dataset per month, region, and product category.
    This dataset will be clean to simulate a structured source.
    """
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Furniture", "Office Supplies"]
    
    # Generate list of first-of-month dates in range
    current_date = start_date.replace(day=1)
    months = []
    while current_date <= end_date:
        months.append(current_date.strftime("%Y-%m-%d"))
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
            
    # Base targets: Electronics > Furniture > Office Supplies
    base_targets = {
        "Electronics": 18000,
        "Furniture": 12000,
        "Office Supplies": 6000
    }
    
    targets = []
    for month in months:
        for region in regions:
            for category in categories:
                # Add some seasonal/regional fluctuation (+/- 20%)
                multiplier = 1.0 + (random.randint(-20, 20) / 100.0)
                # Regional modifiers
                if region == "North":
                    multiplier *= 1.15
                elif region == "West":
                    multiplier *= 1.05
                elif region == "South":
                    multiplier *= 0.90
                
                target_rev = round(base_targets[category] * multiplier, 2)
                targets.append({
                    "Month": month,
                    "Region": region,
                    "Product_Category": category,
                    "Target_Revenue": target_rev
                })
                
    return pd.DataFrame(targets)

if __name__ == "__main__":
    print("Starting Dummy Data Generation script...")
    
    # 12-month period
    end_date = datetime(2026, 5, 31)
    start_date = datetime(2025, 6, 1)
    
    os.makedirs("data/raw", exist_ok=True)
    
    print("Generating raw sales data...")
    sales_df = generate_raw_sales_data(start_date, end_date, num_rows=1600)
    sales_path = "data/raw/raw_sales_data.csv"
    sales_df.to_csv(sales_path, index=False)
    print(f"Generated {len(sales_df)} rows of messy sales data. Saved to '{sales_path}'.")
    
    print("Generating raw targets data...")
    targets_df = generate_targets_data(start_date, end_date)
    targets_path = "data/raw/raw_targets_data.csv"
    targets_df.to_csv(targets_path, index=False)
    print(f"Generated {len(targets_df)} rows of targets data. Saved to '{targets_path}'.")
    
    print("Data generation finished successfully.")
