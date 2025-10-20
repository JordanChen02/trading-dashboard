@echo off
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
  .venv\Scripts\python -m pip install -U pip
  .venv\Scripts\pip install -r requirements.txt
)
start "" .venv\Scripts\python -m streamlit run private_app.py --server.headless=false
