# ZINTOO 👗

### AI-Powered Hyper-Local Fashion Intelligence Platform

**Zintoo** is a next-generation quick-commerce fashion platform designed to deliver apparel within 60 minutes. It combines multimodal search, real-time demand forecasting, and autonomous inventory orchestration to provide a seamless "Try-and-Buy" experience.

---

## ✨ Features

* 🔍 **Multimodal Search** — Search for fashion using text queries (e.g., "casual white kurta") or image uploads powered by **OpenAI CLIP-ViT-B/32**.
* ⚡ **60-Minute Delivery** — Optimized for hyper-local speed with apparel delivered via local dark stores.
* 🤖 **Agentic Orchestration** — Self-correcting inventory logic using **LangGraph** to autonomously reallocate stock between hubs.
* 📈 **Demand Forecasting** — Real-time analytics that predict neighborhood-level trends to ensure popular styles are always in stock.
* 🎨 **Interactive Dashboard** — A sleek **Streamlit** interface for visualizing fashion trends and managing the inventory agent.

---

## 🚀 How to Run the Project

To run the full Zintoo ecosystem, you need to start the **FastAPI Intelligence Layer** and the **Streamlit Dashboard**.

### Terminal 1: Start the Backend (FastAPI & Agents)

1.  Open a new terminal in VS Code.
2.  Activate your virtual environment:
    ```bash
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```
3.  Start the API:
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    *Note: This starts the LangGraph orchestration layer and the CLIP embedding service.*

### Terminal 2: Start the Frontend (Streamlit)

1.  Open a second terminal tab.
2.  Ensure your environment is active and run the dashboard:
    ```bash
    streamlit run app.py
    ```
3.  **Open in Browser**: The dashboard will typically be available at `http://localhost:8501`.

---

## 📁 Directory Structure

```text
zintoo/
├── data/               # Fashion datasets and 7,000+ image samples
├── models/             # CLIP-ViT-B/32 local weights and FAISS indices
├── src/
│   ├── agents/         # LangGraph state machines & inventory logic
│   ├── engine/         # CLIP embedding generation & similarity search
│   ├── api/            # FastAPI endpoints for recommendations
│   └── utils/          # Forecasting and data processing scripts
├── app.py              # Streamlit main dashboard entry point
├── main.py             # FastAPI server entry point
├── requirements.txt    # Project dependencies
└── README.md           # You are here!
