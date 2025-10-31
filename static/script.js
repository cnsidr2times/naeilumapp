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

/* CSRF + Fetch helpers */

let CSRF_TOKEN = null;

async function fetchCsrfToken() {
  try {
    const res = await fetch('/api/csrf_token', { credentials: 'same-origin' });
    const data = await res.json();
    if (data?.success && data?.token) CSRF_TOKEN = data.token;
  } catch (e) {
    console.warn('Failed to fetch CSRF token', e);
  }
}

async function postJSON(url, body = {}) {
  if (!CSRF_TOKEN) await fetchCsrfToken();
  const headers = { 'Content-Type': 'application/json' };
  if (CSRF_TOKEN) headers['X-CSRF-Token'] = CSRF_TOKEN;

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    credentials: 'same-origin'
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch {
    // no-op; allow non-JSON responses to still surface status errors
  }

  if (!res.ok || (payload && payload.success === false)) {
    const msg = payload?.error?.message || res.statusText || 'Request failed';
    throw new Error(msg);
  }
  return payload ?? { success: true };
}

/* Theme helpers */

function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'system') {
    root.removeAttribute('data-theme');
  } else {
    root.setAttribute('data-theme', theme);
  }
}

async function initTheme() {
  try {
    const res = await fetch('/api/theme', { credentials: 'same-origin' });
    const data = await res.json();
    if (data?.success && data.theme) applyTheme(data.theme);
  } catch {
    // ignore – keep default
  }
}

async function toggleTheme() {
  try {
    const data = await postJSON('/api/theme/toggle', {});
    if (data?.success && data.theme) {
      applyTheme(data.theme);
      showToast(`Theme: ${data.theme}`);
    } else {
      throw new Error(data?.error?.message || 'Theme toggle failed');
    }
  } catch (e) {
    console.error('Theme toggle failed:', e);
    showToast(e?.message || 'Theme toggle failed');
  }
}

function setupThemeToggle() {
  // If a toggle already exists in DOM, just wire it up.
  let btn = document.querySelector('.theme-toggle');
  if (!btn) {
    // Create a floating toggle if not present
    btn = document.createElement('button');
    btn.className = 'theme-toggle';
    btn.type = 'button';
    btn.textContent = 'Toggle Theme';
    document.body.appendChild(btn);
  }
  btn.addEventListener('click', toggleTheme);
}

/* Boot */

document.addEventListener('DOMContentLoaded', async () => {
  injectProgressRail();
  injectToast();
  await initTheme();
  setupThemeToggle();

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
  if (name.length > 100) {
    showToast('Name is too long (100 chars max).');
    return;
  }

  currentData.originalName = name;
  currentData.gender = gender;

  showLoading(true);

  try {
    const data = await postJSON('/recommend', { name, gender });

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

    // Accessibility
    card.setAttribute('role', 'button');
    card.setAttribute('aria-selected', 'false');
    card.setAttribute('aria-label', `${nameData.name} – ${nameData.category}`);

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
    const data = await postJSON('/select', { index });

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
  document.querySelectorAll('.name-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-selected', 'false');
  });
  const selectedCard = document.querySelector(`.name-card[data-index="${index}"]`);
  if (selectedCard) {
    selectedCard.classList.add('selected');
    selectedCard.setAttribute('aria-selected', 'true');
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

  // Center ripple if event doesn't have pointer coords (e.g., keyboard-initiated click)
  const hasPointer = typeof event?.clientX === 'number' && typeof event?.clientY === 'number' && (event.clientX !== 0 || event.clientY !== 0);
  const left = hasPointer ? (event.clientX - rect.left - size / 2) : (rect.width / 2 - size / 2);
  const top = hasPointer ? (event.clientY - rect.top - size / 2) : (rect.height / 2 - size / 2);

  ripple.style.left = `${left}px`;
  ripple.style.top = `${top}px`;
  element.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}

function attachCardEnhancements() {
  document.querySelectorAll('.name-card').forEach(card => {
    card.setAttribute('tabindex', '0');
    card.addEventListener('keydown', event => {
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