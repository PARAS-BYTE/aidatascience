"""
Sample dataset generator for development and testing.
Creates realistic tabular datasets with common data quality issues.
"""
import os
import numpy as np
import pandas as pd


def generate_churn_dataset(n_rows: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a customer churn classification dataset.
    Includes: missing values, duplicates, ID column, class imbalance (82/18).
    """
    rng = np.random.RandomState(seed)

    customer_ids = [f"CUST-{i:05d}" for i in range(1, n_rows + 1)]
    ages = rng.normal(42, 14, n_rows).clip(18, 85).astype(int)
    incomes = rng.lognormal(10.8, 0.6, n_rows).clip(15000, 500000).astype(int)
    tenure = rng.exponential(24, n_rows).clip(0, 72).astype(int)
    monthly_charges = rng.normal(65, 30, n_rows).clip(18, 120).round(2)
    total_charges = (monthly_charges * tenure + rng.normal(0, 50, n_rows)).clip(0).round(2)
    support_calls = rng.poisson(1.5, n_rows).clip(0, 15)

    contracts = rng.choice(
        ["Month-to-month", "One year", "Two year"],
        n_rows,
        p=[0.50, 0.30, 0.20]
    )
    payment_methods = rng.choice(
        ["Electronic check", "Mailed check", "Bank transfer", "Credit card"],
        n_rows,
        p=[0.35, 0.20, 0.25, 0.20]
    )
    internet_service = rng.choice(
        ["DSL", "Fiber optic", "No"],
        n_rows,
        p=[0.35, 0.45, 0.20]
    )
    gender = rng.choice(["Male", "Female"], n_rows, p=[0.50, 0.50])
    senior_citizen = rng.choice([0, 1], n_rows, p=[0.84, 0.16])
    partner = rng.choice(["Yes", "No"], n_rows, p=[0.48, 0.52])

    # Generate signup dates
    start_date = pd.Timestamp("2018-01-01")
    days_range = (pd.Timestamp("2024-06-01") - start_date).days
    signup_dates = [start_date + pd.Timedelta(days=int(rng.uniform(0, days_range))) for _ in range(n_rows)]

    # Generate churn with class imbalance (~18% churn)
    churn_prob = np.zeros(n_rows)
    churn_prob += (contracts == "Month-to-month") * 0.15
    churn_prob += (contracts == "One year") * 0.05
    churn_prob += (monthly_charges > 70) * 0.08
    churn_prob += (tenure < 12) * 0.10
    churn_prob += (support_calls > 3) * 0.12
    churn_prob += (internet_service == "Fiber optic") * 0.05
    churn_prob += (payment_methods == "Electronic check") * 0.06
    churn_prob = churn_prob.clip(0.02, 0.65)
    churn = (rng.random(n_rows) < churn_prob).astype(int)
    churn_labels = np.where(churn == 1, "Yes", "No")

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "gender": gender,
        "senior_citizen": senior_citizen,
        "partner": partner,
        "tenure": tenure,
        "internet_service": internet_service,
        "contract_type": contracts,
        "payment_method": payment_methods,
        "monthly_charges": monthly_charges,
        "total_charges": total_charges,
        "support_calls": support_calls,
        "age": ages,
        "income": incomes,
        "signup_date": signup_dates,
        "churn": churn_labels,
    })

    # Inject missing values (~4-5% overall)
    missing_cols = {
        "age": 0.023,
        "income": 0.035,
        "monthly_charges": 0.015,
        "total_charges": 0.04,
        "support_calls": 0.02,
        "internet_service": 0.01,
    }
    for col, pct in missing_cols.items():
        mask = rng.random(n_rows) < pct
        df.loc[mask, col] = np.nan

    # Inject duplicates (~6% of rows)
    n_dupes = int(n_rows * 0.06)
    dupe_indices = rng.choice(n_rows, n_dupes, replace=True)
    dupes = df.iloc[dupe_indices].copy()
    dupes["customer_id"] = [f"CUST-{n_rows + i:05d}" for i in range(1, n_dupes + 1)]
    df = pd.concat([df, dupes], ignore_index=True)

    return df


def generate_house_price_dataset(n_rows: int = 3000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a house price regression dataset.
    Includes: missing values, categorical features, numerical features.
    """
    rng = np.random.RandomState(seed)

    house_ids = [f"H-{i:04d}" for i in range(1, n_rows + 1)]
    house_size = rng.normal(1800, 600, n_rows).clip(400, 6000).astype(int)
    bedrooms = rng.choice([1, 2, 3, 4, 5, 6], n_rows, p=[0.05, 0.15, 0.35, 0.30, 0.12, 0.03])
    bathrooms = rng.choice([1, 1.5, 2, 2.5, 3, 3.5, 4], n_rows, p=[0.10, 0.10, 0.25, 0.20, 0.20, 0.10, 0.05])
    lot_size = (house_size * rng.uniform(1.5, 4.0, n_rows)).astype(int)
    year_built = rng.randint(1950, 2024, n_rows)
    stories = rng.choice([1, 2, 3], n_rows, p=[0.30, 0.55, 0.15])
    garage_cars = rng.choice([0, 1, 2, 3], n_rows, p=[0.10, 0.25, 0.50, 0.15])

    locations = rng.choice(
        ["Downtown", "Suburbs", "Rural", "Waterfront", "Industrial"],
        n_rows,
        p=[0.20, 0.40, 0.20, 0.10, 0.10]
    )
    conditions = rng.choice(
        ["Excellent", "Good", "Average", "Fair", "Poor"],
        n_rows,
        p=[0.10, 0.30, 0.35, 0.18, 0.07]
    )
    has_pool = rng.choice(["Yes", "No"], n_rows, p=[0.20, 0.80])

    # Sale dates
    start_date = pd.Timestamp("2020-01-01")
    days_range = (pd.Timestamp("2024-08-01") - start_date).days
    sale_dates = [start_date + pd.Timedelta(days=int(rng.uniform(0, days_range))) for _ in range(n_rows)]

    # Generate price based on features
    location_multiplier = np.where(
        np.array(locations) == "Downtown", 1.3,
        np.where(np.array(locations) == "Waterfront", 1.5,
        np.where(np.array(locations) == "Suburbs", 1.0,
        np.where(np.array(locations) == "Rural", 0.7, 0.6)))
    )
    condition_multiplier = np.where(
        np.array(conditions) == "Excellent", 1.2,
        np.where(np.array(conditions) == "Good", 1.05,
        np.where(np.array(conditions) == "Average", 1.0,
        np.where(np.array(conditions) == "Fair", 0.85, 0.70)))
    )
    age_factor = 1.0 - (2024 - year_built) * 0.002
    price = (
        house_size * 120
        + bedrooms * 15000
        + bathrooms * 12000
        + garage_cars * 10000
        + lot_size * 5
    ) * location_multiplier * condition_multiplier * age_factor
    price = (price + rng.normal(0, 20000, n_rows)).clip(50000).astype(int)

    df = pd.DataFrame({
        "house_id": house_ids,
        "house_size": house_size,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "lot_size": lot_size,
        "year_built": year_built,
        "stories": stories,
        "garage_cars": garage_cars,
        "location": locations,
        "condition": conditions,
        "has_pool": has_pool,
        "sale_date": sale_dates,
        "price": price,
    })

    # Inject missing values (~3%)
    missing_cols = {
        "lot_size": 0.02,
        "year_built": 0.015,
        "garage_cars": 0.025,
        "condition": 0.01,
    }
    for col, pct in missing_cols.items():
        mask = rng.random(n_rows) < pct
        df.loc[mask, col] = np.nan

    return df


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))

    churn_df = generate_churn_dataset()
    churn_path = os.path.join(output_dir, "customer_churn.csv")
    churn_df.to_csv(churn_path, index=False)
    print(f"Generated customer churn dataset: {churn_df.shape} → {churn_path}")
    print(f"  Churn distribution: {churn_df['churn'].value_counts().to_dict()}")
    print(f"  Missing values: {churn_df.isna().sum().sum()} cells")
    print(f"  Duplicates (excl. ID): {churn_df.drop(columns='customer_id').duplicated().sum()}")

    house_df = generate_house_price_dataset()
    house_path = os.path.join(output_dir, "house_prices.csv")
    house_df.to_csv(house_path, index=False)
    print(f"\nGenerated house prices dataset: {house_df.shape} → {house_path}")
    print(f"  Price range: ${house_df['price'].min():,} - ${house_df['price'].max():,}")
    print(f"  Missing values: {house_df.isna().sum().sum()} cells")
