import torch
import faiss
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io
import os

app = FastAPI()

# --- CONFIGURATION ---
# Paths for your HP Pavilion setup
BASE_PATH = r"D:\FASHION\fashion-small\myntradataset"
IMAGE_DIR = os.path.join(BASE_PATH, "images")
# Using the NEWly synced data from your 7,000 item reindex
SYNCED_CSV = r"D:\FASHION\data\products.csv"
SYNCED_INDEX = r"D:\FASHION\data\fashion.index"

# 1. Load Data
# We load the version created by reindex.py to ensure perfect row-to-vector matching
df = pd.read_csv(SYNCED_CSV)
df['id'] = df['id'].astype(int)

# 2. Load FAISS Index
index = faiss.read_index(SYNCED_INDEX)

# 3. Load CLIP Model
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Running on: {device}")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model.eval()

# 4. Serve Static Images
# This allows app.py to fetch images via http://localhost:8000/images/ID.jpg
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

# --- CORE FUNCTIONS ---

def get_text_embedding(text):
    inputs = processor(text=[text], return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs)
        emb = outputs if isinstance(outputs, torch.Tensor) else outputs.pooler_output
        # Normalization is key for accurate 'Confidence' scores
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy()

def get_image_embedding(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=img, return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        emb = outputs if isinstance(outputs, torch.Tensor) else outputs.pooler_output
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy()

# --- API ENDPOINTS ---

@app.get("/search")
def search(query: str, top_k: int = 9):
    emb = get_text_embedding(query)
    # FAISS returns distances and indices
    distances, indices = index.search(emb.astype('float32'), top_k)
    
    results_list = []
    for i, idx in enumerate(indices[0]):
        item = df.iloc[idx].to_dict()
        # Convert numpy float32 to standard python float for JSON compatibility
        item['similarity_score'] = float(distances[0][i])
        results_list.append(item)
    
    return {"results": results_list}

@app.post("/search_image")
async def search_image(file: UploadFile = File(...)):
    content = await file.read()
    emb = get_image_embedding(content)
    distances, indices = index.search(emb.astype('float32'), 9)
    
    results_list = []
    for i, idx in enumerate(indices[0]):
        item = df.iloc[idx].to_dict()
        item['similarity_score'] = float(distances[0][i])
        results_list.append(item)
        
    return {"results": results_list}

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)