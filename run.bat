@echo off
set GOOGLE_API_KEY=YOUR_API_KEY
uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000
