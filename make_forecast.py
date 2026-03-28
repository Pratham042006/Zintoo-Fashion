import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load your synced products
df_products = pd.read_csv(r"D:\FASHION\data\products.csv")

# Generate synthetic demand data for the last 30 days + next 7 days forecast
data = []
pincodes = [560001, 560037, 560064] # Bangalore pincodes

# Focus on the top 10 products for the demo to keep the UI snappy
for _, product in df_products.head(10).iterrows(): 
    for pc in pincodes:
        # Base daily demand for this specific product/pincode
        base_demand = np.random.randint(5, 15) 
        
        # 30 days past (-30 to 0) + 7 days future (1 to 7)
        for i in range(-30, 8): 
            # Force daily granularity by adding exactly 'i' days
            date_obj = datetime.now() + timedelta(days=i)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Logic: If it's a forecast (i > 0), add a slight "upward trend" 
            # to make the Agent's reallocation orders more likely to trigger
            trend = np.random.randint(2, 6) if i > 0 else np.random.randint(-2, 3)
            demand = max(1, base_demand + trend) 
            
            is_forecast = i > 0
            
            data.append([
                int(product['id']), 
                product['productDisplayName'], 
                pc, 
                date_str, 
                demand, 
                is_forecast
            ])

df_forecast = pd.DataFrame(data, columns=['id', 'name', 'pincode', 'date', 'demand', 'is_forecast'])

# Final Step: Save to the data folder
df_forecast.to_csv(r"D:\FASHION\data\demand_forecast.csv", index=False)
print(f"Success: Daily Demand Forecast generated for {len(df_forecast)} rows.")