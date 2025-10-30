# Naeilum - Korean Name Finder

Naeilum (내일:음 - Tomorrow's Sound) is a web application that helps international friends discover meaningful Korean names that resonate with their identity.

## Features

- **Personalized Korean Name Recommendations**: Get 5 curated Korean names based on your input
- **Meaningful Names with Hanja**: Each name comes with Chinese characters and cultural meaning
- **Daily Fortune**: Unique fortune readings based on your Korean name
- **Privacy-First**: No personal data is stored permanently
- **Beautiful UI**: Modern, responsive design with smooth animations
- **Back Button Navigation**: Easy navigation between screens

## Installation

### Requirements
- Python 3.8 or higher
- Flask 2.3.3

### Setup Instructions

1. **Extract the ZIP file** to your desired location

2. **Navigate to the app directory**:
   ```bash
   cd naeilum_app
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

## File Structure

```
naeilum_app/
│
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── static/               # Static files
│   ├── style.css        # Styles
│   └── script.js        # JavaScript
│
├── templates/            # HTML templates
│   ├── index.html       # Main app page
│   ├── about.html       # About page
│   └── privacy.html     # Privacy policy
│
├── names_male.json      # Male Korean names database
├── names_female.json    # Female Korean names database
└── fortunes.json        # Fortune messages
```

## How to Use

1. **Start**: Click "Get Started" on the welcome screen
2. **Enter Your Name**: Type your name and select gender preference
3. **Choose a Korean Name**: Select from 5 personalized recommendations
4. **View Your Name**: See your Korean name with meaning and Hanja
5. **Check Fortune**: View your daily fortune (changes every day!)
6. **Navigate Back**: Use the back button (← Back) to go to previous screens

## Special Feature

Try entering "Wilson Smith" as a male name for a special surprise! 🎉

## Name Categories

Names are organized by meaningful categories:
- **Wisdom** (지혜): Intelligence and understanding
- **Courage** (용기): Bravery and strength
- **Beauty** (아름다움): Grace and elegance
- **Love** (사랑): Warmth and affection
- **Hope** (희망): Bright future wishes
- **Harmony** (조화): Balance and peace
- **Growth** (성장): Evolution and progress
- **Faith** (신념): Trust and belief
- And more...

## Privacy

- No personal data is permanently stored
- Session data is cleared when you close your browser
- No tracking or analytics
- Completely anonymous usage

## Troubleshooting

### Port already in use
If you see an error about port 5000 being in use, you can change the port:
```bash
python app.py
```
Then modify the last line in app.py to use a different port:
```python
app.run(debug=False, host='0.0.0.0', port=5001)
```

### Dependencies not installing
Make sure you have pip installed and updated:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Application not loading
- Check that all files are in the correct directories
- Ensure Python 3.8+ is installed
- Try clearing your browser cache

## Browser Compatibility

Works best with modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development

To run in development mode with auto-reload:
```python
# In app.py, change the last line to:
app.run(debug=True, host='0.0.0.0', port=5000)
```

## Credits

Created with ❤️ for cultural exchange and friendship.

## License

This project is provided as-is for personal and educational use.

---

**Enjoy discovering your Korean name!**
