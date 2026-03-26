import pandas as pd
import numpy as np

# Load your 1000 synced products
df_products = pd.read_csv(r"D:\FASHION\data\products.csv")

# Create 3 Warehouses
warehouses = ['W1 (North BLR)', 'W2 (South BLR)', 'W3 (Central Hub)']
inventory_data = []

for _, product in df_products.iterrows():
    for wh in warehouses:
        stock = np.random.randint(5, 50)
        inventory_data.append([product['id'], product['productDisplayName'], wh, stock])

df_inventory = pd.DataFrame(inventory_data, columns=['id', 'name', 'warehouse', 'stock'])
df_inventory.to_csv(r"D:\FASHION\data\warehouse_inventory.csv", index=False)
print("Warehouse Inventory initialized!")