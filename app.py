#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Naeilum (내일:음) - Korean Name Recommendation App
A Flask application that recommends Korean names for foreigners
"""

from flask import Flask, render_template, request, session, jsonify, redirect, url_for
import json
import random
import hashlib
import os
from datetime import datetime, timedelta
import secrets
import unicodedata
import re

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=7)

# Load name data
def load_names():
    """Load Korean names from JSON files"""
    names_data = {'male': [], 'female': []}

    try:
        # Load male names
        json_path = os.path.join(os.path.dirname(__file__), 'names_male.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            names_data['male'] = json.load(f)

        # Load female names  
        json_path = os.path.join(os.path.dirname(__file__), 'names_female.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            names_data['female'] = json.load(f)

    except Exception as e:
        print(f"Error loading names: {e}")
        # Fallback data if files not found
        names_data = generate_fallback_names()

    return names_data

def generate_fallback_names():
    """Generate fallback name data if JSON files are not available"""
    return {
        'male': [
            {
                'name': '송월선',
                'hanja': '宋蔚宣',
                'category': 'Wisdom',
                'meaning': 'One who proclaims great wisdom like a pine tree',
                'initial': 'W',
                'special_match': 'Wilson Smith'
            }
        ],
        'female': []
    }

def load_fortunes():
    """Load fortune messages from JSON file"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'fortunes.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Fallback fortunes
        return [
            {
                "category": "Love",
                "messages": ["Love finds you when you're true to yourself"]
            },
            {
                "category": "Career",
                "messages": ["Your dedication will be recognized soon"]
            },
            {
                "category": "Wealth", 
                "messages": ["Financial wisdom comes through patient planning"]
            },
            {
                "category": "Health",
                "messages": ["Your body thanks you for mindful choices"]
            },
            {
                "category": "Wisdom",
                "messages": ["A lesson from the past illuminates your path"]
            }
        ]

# Load data on startup
NAMES_DATA = load_names()
FORTUNES_DATA = load_fortunes()

def normalize_name(name):
    """Normalize name for matching - remove spaces, convert to lowercase"""
    # Remove accents and normalize unicode
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    # Remove non-alphanumeric characters and convert to lowercase
    name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return name

def get_name_initial(name):
    """Extract the first letter of the first name"""
    # Split by space and get first part
    parts = name.strip().split()
    if parts:
        first_name = parts[0]
        # Remove non-alphabetic characters and get first letter
        clean_name = re.sub(r'[^a-zA-Z]', '', first_name)
        if clean_name:
            return clean_name[0].upper()
    return 'A'  # Default

def generate_session_id():
    """Generate anonymous session ID"""
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]

def select_korean_names(original_name, gender):
    """Select Korean names based on the original name"""
    names = []

    # Normalize the input name for matching
    normalized_input = normalize_name(original_name)

    # Special case: Check for Wilson Smith
    if normalized_input == 'wilsonsmith':
        # Return the special name for Wilson Smith
        for name in NAMES_DATA.get('male', []):
            if name.get('special_match') == 'Wilson Smith':
                names.append(name)
                break
        # Add more random names to fill up to 5
        gender_names = NAMES_DATA.get('male', [])
        available_names = [n for n in gender_names if not n.get('special_match')]
        if available_names:
            random.shuffle(available_names)
            names.extend(available_names[:4])
        return names[:5]

    # Regular name selection logic
    gender_names = NAMES_DATA.get(gender, [])
    if not gender_names:
        return []

    # Get the initial letter
    initial = get_name_initial(original_name)

    # Filter names by initial if available
    matching_names = []
    for name in gender_names:
        if not name.get('special_match'):  # Skip special match names
            if name.get('initial') == initial:
                matching_names.append(name)

    # If no names match the initial, use all names
    if not matching_names:
        matching_names = [n for n in gender_names if not n.get('special_match')]

    # Randomly select up to 5 names
    if matching_names:
        random.shuffle(matching_names)
        names = matching_names[:5]

    return names

def get_daily_fortune(korean_name):
    """Generate daily fortune based on Korean name"""
    # Create seed from name and today's date
    today = datetime.now().strftime('%Y-%m-%d')
    seed_string = f"{korean_name}{today}"
    random.seed(hashlib.md5(seed_string.encode()).hexdigest())

    fortunes = []
    for category_data in FORTUNES_DATA:
        category = category_data['category']
        messages = category_data['messages']
        if messages:
            message = random.choice(messages)
            fortunes.append({
                'category': category,
                'message': message
            })

    # Reset random seed
    random.seed()

    return fortunes

@app.route('/')
def index():
    """Main page"""
    session.permanent = True
    if 'session_id' not in session:
        session['session_id'] = generate_session_id()
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    """Process name and return recommendations"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    original_name = data.get('name', '').strip()
    gender = data.get('gender', 'male')

    if not original_name:
        return jsonify({'error': 'Name is required'}), 400

    # Store in session
    session['original_name'] = original_name
    session['gender'] = gender

    # Generate Korean names
    korean_names = select_korean_names(original_name, gender)

    if not korean_names:
        return jsonify({'error': 'Could not generate names'}), 500

    # Store recommendations in session
    session['recommendations'] = korean_names

    return jsonify({
        'success': True,
        'names': korean_names
    })

@app.route('/select', methods=['POST'])
def select():
    """Handle name selection"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    selected_index = data.get('index', 0)
    recommendations = session.get('recommendations', [])

    if selected_index >= len(recommendations):
        return jsonify({'error': 'Invalid selection'}), 400

    selected_name = recommendations[selected_index]
    session['selected_name'] = selected_name

    # Generate fortune
    fortune = get_daily_fortune(selected_name['name'])
    session['fortune'] = fortune

    return jsonify({
        'success': True,
        'name': selected_name,
        'fortune': fortune
    })

@app.route('/save_preference', methods=['POST'])
def save_preference():
    """Save user preference (stored in session only)"""
    data = request.get_json()
    save = data.get('save', False)

    session['save_preference'] = save

    if save:
        # In a real app, this would save to a database
        # For privacy, we only store in session
        session['saved_data'] = {
            'timestamp': datetime.now().isoformat(),
            'original_name': session.get('original_name'),
            'selected_name': session.get('selected_name'),
            'session_id': session.get('session_id')
        }

    return jsonify({'success': True})

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
