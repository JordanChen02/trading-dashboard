#!/bin/bash
[[ -d .venv ]] || python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python -m streamlit run private_app.py --server.headless=false
