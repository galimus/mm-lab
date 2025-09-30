#!/bin/bash
set -e  

echo " Setting up environment..."


if [ ! -d ".venv" ]; then
  echo " Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate


echo " Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

DEBUG_MODE=0
if [[ "$1" == "debug" ]]; then
  DEBUG_MODE=1
  echo " Debug mode enabled"
fi

echo " Launching Streamlit app..."
PYTHONPATH=. streamlit run streamlit_app/app.py -- --debug_mode $DEBUG_MODE
