// Naeilum JavaScript - English UI with Back Button Support

// Screen navigation history for back button
let screenHistory = [];
let currentData = {
    originalName: '',
    gender: 'male',
    recommendations: [],
    selectedName: null,
    fortune: []
};

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Initialize with welcome screen
    screenHistory = ['welcome-screen'];
    showScreen('welcome-screen');

    // Form submission handler
    const nameForm = document.getElementById('name-form');
    if (nameForm) {
        nameForm.addEventListener('submit', handleNameSubmit);
    }

    // Set today's date for fortune
    const today = new Date();
    const dateElement = document.getElementById('fortune-date');
    if (dateElement) {
        dateElement.textContent = today.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
});

// Show specific screen
function showScreen(screenId) {
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.classList.remove('active');
    });

    // Show target screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
    }

    // Update history if not going back
    if (screenHistory[screenHistory.length - 1] !== screenId) {
        screenHistory.push(screenId);
    }
}

// Go back to previous screen
function goBack(targetScreen) {
    // Remove current screen from history
    if (screenHistory.length > 1) {
        screenHistory.pop();
    }

    // Show the target screen or the previous one
    if (targetScreen) {
        showScreen(targetScreen);
        // Update history to match
        screenHistory = screenHistory.filter(s => s !== targetScreen);
        screenHistory.push(targetScreen);
    } else if (screenHistory.length > 0) {
        showScreen(screenHistory[screenHistory.length - 1]);
    }
}

// Show name input screen
function showNameInput() {
    showScreen('name-input-screen');
}

// Handle name form submission
async function handleNameSubmit(event) {
    event.preventDefault();

    const name = document.getElementById('name').value.trim();
    const gender = document.querySelector('input[name="gender"]:checked').value;

    if (!name) {
        alert('Please enter your name');
        return;
    }

    currentData.originalName = name;
    currentData.gender = gender;

    // Show loading
    showLoading(true);

    try {
        // Send request to get Korean names
        const response = await fetch('/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                gender: gender
            })
        });

        const data = await response.json();

        if (data.success) {
            currentData.recommendations = data.names;
            displayNameCards(data.names);
            showScreen('selection-screen');
        } else {
            alert('Error: ' + (data.error || 'Failed to get recommendations'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to connect to the server. Please try again.');
    } finally {
        showLoading(false);
    }
}

// Display name cards for selection
function displayNameCards(names) {
    const container = document.getElementById('name-cards');
    container.innerHTML = '';

    names.forEach((nameData, index) => {
        const card = document.createElement('div');
        card.className = 'name-card';
        card.onclick = () => selectName(index);

        // Category colors
        const categoryColors = {
            'Wisdom': '#4A90E2',
            'Courage': '#FF6B6B',
            'Beauty': '#7B68EE',
            'Love': '#FF69B4',
            'Hope': '#FFD700',
            'Harmony': '#4CAF50',
            'Peace': '#87CEEB',
            'Growth': '#98D8C8',
            'Faith': '#DDA0DD',
            'Strength': '#FF7F50',
            'Honor': '#B8860B',
            'Justice': '#4682B4',
            'Unity': '#9370DB',
            'Vision': '#20B2AA',
            'Light': '#FFE4B5'
        };

        const categoryColor = categoryColors[nameData.category] || '#4A90E2';

        card.innerHTML = `
            <div class="name-card-header">
                <div>
                    <span class="korean-name">${nameData.name}</span>
                    <span class="hanja">${nameData.hanja}</span>
                </div>
            </div>
            <div class="name-meaning">${nameData.meaning}</div>
            <span class="name-category-badge" style="background: ${categoryColor}">
                ${nameData.category}
            </span>
        `;

        container.appendChild(card);
    });
}

// Select a Korean name
async function selectName(index) {
    if (index >= currentData.recommendations.length) {
        return;
    }

    const selectedName = currentData.recommendations[index];
    currentData.selectedName = selectedName;

    showLoading(true);

    try {
        // Send selection to server
        const response = await fetch('/select', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                index: index
            })
        });

        const data = await response.json();

        if (data.success) {
            currentData.fortune = data.fortune;
            displayResult(selectedName);
            showScreen('result-screen');
        } else {
            alert('Error: ' + (data.error || 'Failed to process selection'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to process selection. Please try again.');
    } finally {
        showLoading(false);
    }
}

// Display the selected name result
function displayResult(nameData) {
    document.getElementById('korean-name-large').textContent = nameData.name;
    document.getElementById('korean-name-hanja').textContent = nameData.hanja;
    document.getElementById('name-meaning-text').textContent = nameData.meaning;
    document.getElementById('name-category').textContent = nameData.category;
    document.getElementById('original-name-display').textContent = currentData.originalName;
}

// Show fortune screen
function showFortune() {
    if (currentData.fortune && currentData.fortune.length > 0) {
        displayFortune(currentData.fortune);
        showScreen('fortune-screen');
    }
}

// Display fortune cards
function displayFortune(fortunes) {
    const container = document.getElementById('fortune-cards');
    container.innerHTML = '';

    // Fortune category icons/colors
    const fortuneStyles = {
        'Love': { color: '#FF69B4', icon: '❤️' },
        'Career': { color: '#4A90E2', icon: '💼' },
        'Wealth': { color: '#FFD700', icon: '💰' },
        'Health': { color: '#4CAF50', icon: '🌿' },
        'Wisdom': { color: '#7B68EE', icon: '🔮' }
    };

    fortunes.forEach(fortune => {
        const style = fortuneStyles[fortune.category] || { color: '#4A90E2', icon: '⭐' };

        const card = document.createElement('div');
        card.className = 'fortune-card';
        card.style.borderLeftColor = style.color;

        card.innerHTML = `
            <div class="fortune-category" style="color: ${style.color}">
                ${style.icon} ${fortune.category}
            </div>
            <div class="fortune-message">${fortune.message}</div>
        `;

        container.appendChild(card);
    });
}

// Start over
function startOver() {
    // Reset data
    currentData = {
        originalName: '',
        gender: 'male',
        recommendations: [],
        selectedName: null,
        fortune: []
    };

    // Clear form
    const nameInput = document.getElementById('name');
    if (nameInput) {
        nameInput.value = '';
    }

    // Reset radio buttons
    const maleRadio = document.querySelector('input[name="gender"][value="male"]');
    if (maleRadio) {
        maleRadio.checked = true;
    }

    // Reset history and go to welcome screen
    screenHistory = ['welcome-screen'];
    showScreen('welcome-screen');
}

// Show/hide loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
}

// Keyboard navigation support
document.addEventListener('keydown', function(event) {
    // ESC key to go back
    if (event.key === 'Escape') {
        const currentScreen = screenHistory[screenHistory.length - 1];
        const backButton = document.querySelector(`#${currentScreen} .back-button`);
        if (backButton) {
            backButton.click();
        }
    }
});