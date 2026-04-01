import torch
import faiss
import pandas as pd
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from tqdm import tqdm
import os

# --- CONFIG ---
CSV_PATH = r"D:\FASHION\fashion-small\myntradataset\styles.csv"
IMAGE_DIR = r"D:\FASHION\fashion-small\myntradataset\images"
SAVE_DIR = r"D:\FASHION\data"

# Create data folder if missing
os.makedirs(SAVE_DIR, exist_ok=True)

# 1. Load Model
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using: {device}")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model.eval()

# 2. Load and Filter CSV
df = pd.read_csv(CSV_PATH, on_bad_lines='skip')
# Keep only rows where images actually exist locally
df['exists'] = df['id'].apply(lambda x: os.path.exists(os.path.join(IMAGE_DIR, f"{int(x)}.jpg")))
df = df[df['exists']].head(7000).reset_index(drop=True)
print(f"Indexing {len(df)} local products...")

# 3. Generate Embeddings
all_embeddings = []
for i, row in tqdm(df.iterrows(), total=len(df)):
    img_path = os.path.join(IMAGE_DIR, f"{int(row['id'])}.jpg")
    img = Image.open(img_path).convert("RGB")
    
    inputs = processor(images=img, return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        emb = outputs if isinstance(outputs, torch.Tensor) else outputs.pooler_output
        emb = emb / emb.norm(dim=-1, keepdim=True)
        all_embeddings.append(emb.cpu().numpy())

# 4. Build Index
embeddings_np = np.vstack(all_embeddings).astype('float32')
dimension = embeddings_np.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings_np)

# 5. Save Everything
faiss.write_index(index, os.path.join(SAVE_DIR, "fashion.index"))
df.drop(columns=['exists']).to_csv(os.path.join(SAVE_DIR, "products.csv"), index=False)
print("SUCCESS: Index and CSV are now perfectly synced!")