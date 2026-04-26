const API_URL = 'http://127.0.0.1:5000/api';

// UI Elements
const loginSection = document.getElementById('loginSection');
const signupSection = document.getElementById('signupSection');
const showSignupBtn = document.getElementById('showSignup');
const showLoginBtn = document.getElementById('showLogin');

const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const loginAlert = document.getElementById('loginAlert');
const signupAlert = document.getElementById('signupAlert');

// Check if already logged in
if (localStorage.getItem('fairaid_token')) {
    window.location.href = 'dashboard.html';
}

// Toggle Forms
showSignupBtn.addEventListener('click', (e) => {
    e.preventDefault();
    loginSection.classList.add('hidden');
    signupSection.classList.remove('hidden');
});

showLoginBtn.addEventListener('click', (e) => {
    e.preventDefault();
    signupSection.classList.add('hidden');
    loginSection.classList.remove('hidden');
});

function showAlert(element, message, isSuccess = false) {
    element.textContent = message;
    element.className = `alert ${isSuccess ? 'bg-success status-success' : 'bg-error status-error'} show`;
}

// Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const btn = e.target.querySelector('button');

    btn.disabled = true;
    btn.textContent = 'Signing in...';

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            localStorage.setItem('fairaid_token', data.token);
            localStorage.setItem('fairaid_ngo', data.ngo_name);
            window.location.href = 'dashboard.html';
        } else {
            showAlert(loginAlert, data.message || 'Login failed');
        }
    } catch (err) {
        showAlert(loginAlert, 'Server connection failed. Is backend running?');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
});

// Signup
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ngo_name = document.getElementById('signupNgoName').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    const btn = e.target.querySelector('button');

    btn.disabled = true;
    btn.textContent = 'Registering...';

    try {
        const res = await fetch(`${API_URL}/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ngo_name, email, password })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showAlert(signupAlert, 'Registration successful! Please login.', true);
            setTimeout(() => {
                showLoginBtn.click();
                document.getElementById('loginEmail').value = email;
            }, 1500);
        } else {
            showAlert(signupAlert, data.message || 'Registration failed');
        }
    } catch (err) {
        showAlert(signupAlert, 'Server connection failed.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Register NGO';
    }
});
