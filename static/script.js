// Naeilum UI scripts with step navigation, ripple feedback, and toast messages.

const stepOrder = ['welcome-screen', 'name-input-screen', 'selection-screen', 'result-screen', 'fortune-screen'];
const screenTitles = {
    'welcome-screen': 'Start',
    'name-input-screen': 'Tell Us About You',
    'selection-screen': 'Choose Name',
    'result-screen': 'Your Name',
    'fortune-screen': 'Daily Fortune'
};

let screenHistory = [];
let currentData = {
    originalName: '',
    gender: 'male',
    recommendations: [],
    selectedName: null,
    fortune: []
};

document.addEventListener('DOMContentLoaded', () => {
    injectProgressRail();
    injectToast();

    screenHistory = ['welcome-screen'];
    showScreen('welcome-screen', { skipHistory: true });

    const getStartedBtn = document.getElementById('get-started-btn');
    if (getStartedBtn) {
        getStartedBtn.addEventListener('click', event => {
            event.preventDefault();
            showNameInput();
        });
    }

    const nameForm = document.getElementById('name-form');
    if (nameForm) {
        nameForm.addEventListener('submit', handleNameSubmit);
    }

    const dateElement = document.getElementById('fortune-date');
    if (dateElement) {
        const today = new Date();
        dateElement.textContent = today.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
});

/* Screen navigation */

function showScreen(screenId, options = {}) {
    const { skipHistory = false } = options;

    document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));

    const targetScreen = document.getElementById(screenId);
    if (!targetScreen) return;

    targetScreen.classList.add('active');

    if (!skipHistory && screenHistory[screenHistory.length - 1] !== screenId) {
        screenHistory.push(screenId);
    }

    updateProgressRail(screenId);
    focusFirstField(screenId);

    if (screenId === 'selection-screen') {
        attachCardEnhancements();
    }
}

function goBack(targetScreenId) {
    if (screenHistory.length > 1) {
        screenHistory.pop();
    }

    if (targetScreenId) {
        showScreen(targetScreenId, { skipHistory: true });
        screenHistory = screenHistory.filter(screen => screen !== targetScreenId);
        screenHistory.push(targetScreenId);
    } else if (screenHistory.length > 0) {
        showScreen(screenHistory[screenHistory.length - 1], { skipHistory: true });
    }
}

function showNameInput() {
    showScreen('name-input-screen');
}

/* Form handling */

async function handleNameSubmit(event) {
    event.preventDefault();

    const nameInput = document.getElementById('name');
    const genderInput = document.querySelector('input[name="gender"]:checked');

    if (!nameInput || !genderInput) {
        showToast('Please enter your name and select a gender.');
        return;
    }

    const name = nameInput.value.trim();
    const gender = genderInput.value;

    if (!name) {
        showToast('Name field cannot be empty.');
        return;
    }

    currentData.originalName = name;
    currentData.gender = gender;

    showLoading(true);

    try {
        const response = await fetch('/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, gender })
        });

        const data = await response.json();

        if (data.success) {
            currentData.recommendations = data.names;
            displayNameCards(data.names);
            showScreen('selection-screen');
            showToast('Recommendations ready ✨');
        } else {
            const errMsg = data.error?.message || data.error || 'Failed to get recommendations.';
            showToast(`Error: ${errMsg}`);
        }
    } catch (error) {
        console.error('Recommendation error:', error);
        showToast('Connection issue – please try again.');
    } finally {
        showLoading(false);
    }
}

/* Name selection */

function displayNameCards(names) {
    const container = document.getElementById('name-cards');
    if (!container) return;

    container.innerHTML = '';

    const categoryPalette = {
        Strength: '#234B7A',
        Light: '#6C8CC9',
        Honor: '#BD6B5F',
        Wisdom: '#4E6FA6',
        Justice: '#233A58',
        Love: '#C27A7A',
        Harmony: '#3A8570',
        Prosperity: '#C9A86A'
    };

    names.forEach((nameData, index) => {
        const card = document.createElement('div');
        card.className = 'name-card';
        card.dataset.index = index;

        const categoryColor = categoryPalette[nameData.category] || '#234B7A';

        card.innerHTML = `
            <div class="name-card-header">
                <div>
                    <span class="korean-name">${nameData.name}</span>
                    <span class="hanja">${nameData.hanja}</span>
                </div>
            </div>
            <div class="name-meaning">${nameData.meaning}</div>
            <span class="name-category-badge" style="color:${categoryColor}; border-color:${categoryColor}33; background:${categoryColor}14;">
                ${nameData.category}
            </span>
        `;

        card.addEventListener('click', event => {
            createRipple(event, card);
            selectName(index);
        });

        container.appendChild(card);
    });
}

async function selectName(index) {
    if (index >= currentData.recommendations.length) return;

    highlightSelectedCard(index);
    currentData.selectedName = currentData.recommendations[index];

    showLoading(true);

    try {
        const response = await fetch('/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
        });

        const data = await response.json();

        if (data.success) {
            currentData.fortune = data.fortune;
            displayResult(currentData.selectedName);
            showScreen('result-screen');
            showToast('Name locked in! 🌿');
        } else {
            const errMsg = data.error?.message || data.error || 'Failed to process selection.';
            showToast(`Error: ${errMsg}`);
        }
    } catch (error) {
        console.error('Selection error:', error);
        showToast('Something went wrong. Try again?');
    } finally {
        showLoading(false);
    }
}

function highlightSelectedCard(index) {
    document.querySelectorAll('.name-card').forEach(card => card.classList.remove('selected'));
    const selectedCard = document.querySelector(`.name-card[data-index="${index}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
}

function displayResult(nameData) {
    const nameLarge = document.getElementById('korean-name-large');
    const nameHanja = document.getElementById('korean-name-hanja');
    const meaningText = document.getElementById('name-meaning-text');
    const categoryText = document.getElementById('name-category');
    const originalName = document.getElementById('original-name-display');

    if (nameLarge) nameLarge.textContent = nameData.name;
    if (nameHanja) nameHanja.textContent = nameData.hanja;
    if (meaningText) meaningText.textContent = nameData.meaning;
    if (categoryText) categoryText.textContent = nameData.category;
    if (originalName) originalName.textContent = currentData.originalName;
}

/* Fortune flow */

function showFortune() {
    if (currentData.fortune && currentData.fortune.length > 0) {
        displayFortune(currentData.fortune);
        showScreen('fortune-screen');
        showToast('Daily fortune revealed ☀️');
    }
}

function displayFortune(fortunes) {
    const container = document.getElementById('fortune-cards');
    if (!container) return;

    container.innerHTML = '';

    const fortuneStyles = {
        Love: { color: '#BD6B5F', icon: '♥' },
        Career: { color: '#234B7A', icon: '💼' },
        Wealth: { color: '#C9A86A', icon: '◆' },
        Health: { color: '#3A8570', icon: '✧' },
        Wisdom: { color: '#4E6FA6', icon: '✦' }
    };

    fortunes.forEach(fortune => {
        const style = fortuneStyles[fortune.category] || { color: '#234B7A', icon: '✶' };
        const card = document.createElement('div');
        card.className = 'fortune-card';
        card.style.borderLeft = `4px solid ${style.color}`;

        card.innerHTML = `
            <div class="fortune-category" style="color:${style.color}">
                ${style.icon} ${fortune.category}
            </div>
            <div class="fortune-message">${fortune.message}</div>
        `;

        container.appendChild(card);
    });
}

/* Reset */

function startOver() {
    currentData = {
        originalName: '',
        gender: 'male',
        recommendations: [],
        selectedName: null,
        fortune: []
    };

    const nameInput = document.getElementById('name');
    if (nameInput) nameInput.value = '';

    const maleRadio = document.querySelector('input[name="gender"][value="male"]');
    if (maleRadio) maleRadio.checked = true;

    screenHistory = ['welcome-screen'];
    showScreen('welcome-screen', { skipHistory: true });
    showToast('Reset complete.');
}

/* Utilities */

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    overlay.classList.toggle('active', !!show);
}

function createRipple(event, element) {
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
    element.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
}

function attachCardEnhancements() {
    document.querySelectorAll('.name-card').forEach(card => {
        card.setAttribute('tabindex', '0');
        card.addEventListener('keypress', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                card.click();
            }
        });
    });
}

function injectProgressRail() {
    if (document.querySelector('.progress-rail')) return;

    const container = document.querySelector('.container');
    if (!container) return;

    const rail = document.createElement('div');
    rail.className = 'progress-rail';
    rail.id = 'progress-rail';
    rail.setAttribute('role', 'tablist');
    rail.setAttribute('aria-label', 'Onboarding steps');

    stepOrder.forEach(stepId => {
        const stepEl = document.createElement('div');
        stepEl.className = 'progress-step';
        stepEl.dataset.step = stepId;
        stepEl.textContent = screenTitles[stepId];
        rail.appendChild(stepEl);
    });

    container.prepend(rail);
    updateProgressRail('welcome-screen');
}

function updateProgressRail(activeScreenId) {
    document.querySelectorAll('.progress-step').forEach(step => step.classList.remove('active'));
    const activeStep = document.querySelector(`.progress-step[data-step="${activeScreenId}"]`);
    if (activeStep) activeStep.classList.add('active');
}

function focusFirstField(screenId) {
    if (screenId === 'name-input-screen') {
        const input = document.getElementById('name');
        if (input) setTimeout(() => input.focus(), 220);
    }
}

function injectToast() {
    if (document.querySelector('.toast')) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.id = 'toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
}

let toastTimeout;
function showToast(message = '') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => toast.classList.remove('show'), 2600);
}

/* Keyboard support */

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        const currentScreen = screenHistory[screenHistory.length - 1];
        const backButton = document.querySelector(`#${currentScreen} .back-button`);
        if (backButton) backButton.click();
    }
});