#!/bin/bash
echo "Starting Naeilum Korean Name Finder..."
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo ""
echo "Starting server..."
echo ""
echo "========================================"
echo "Naeilum is running!"
echo "Open your browser and go to:"
echo "http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""
python3 app.py