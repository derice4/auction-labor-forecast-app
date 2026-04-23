# 🚗 Auto Auction Labor Forecasting

A end-to-end labor forecasting pipeline built with Python, SQL, and the Claude AI API — simulating real-world workforce planning for an auto auction facility.

Built as a portfolio project to demonstrate skills in data engineering, analytics, and AI integration for operations-focused roles.

## Tech Stack
- Python 3.10+
- SQLite
- SQL + pandas
- Claude API
- Streamlit + Plotly
- Jupyter Notebook

## How to Run

1. Install dependencies: pip install -r requirements.txt
2. Generate the data: python data/generate_data.py
3. Run the dashboard: streamlit run app/streamlit_app.py

## Project Structure

- data/ - Synthetic data generator
- sql/ - Core SQL forecasting queries
- forecast/ - Python forecasting engine and AI summary module
- app/ - Streamlit dashboard
- notebooks/ - Jupyter analysis notebook

## API Key Setup

Create a .env file in the root folder with:
ANTHROPIC_API_KEY=your-key-here