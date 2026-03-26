import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load your synced products
df_products = pd.read_csv(r"D:\FASHION\data\products.csv")

# Generate synthetic demand data for the last 30 days + next 7 days forecast
data = []
pincodes = [560001, 560037, 560064] # Bangalore pincodes

for _, product in df_products.head(10).iterrows(): # Just do top 10 for the demo
    for pc in pincodes:
        base_demand = np.random.randint(5, 20)
        for i in range(-30, 8): # 30 days past, 7 days future
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            # Add some randomness and a "trend" for the future
            demand = max(0, base_demand + np.random.randint(-3, 5))
            is_forecast = i > 0
            data.append([product['id'], product['productDisplayName'], pc, date, demand, is_forecast])

df_forecast = pd.DataFrame(data, columns=['id', 'name', 'pincode', 'date', 'demand', 'is_forecast'])
df_forecast.to_csv(r"D:\FASHION\data\demand_forecast.csv", index=False)
print("Demand Forecast data generated!")