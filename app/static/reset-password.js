const API = '';

function getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

if (typeof feather !== 'undefined') feather.replace();

const token = getQueryParam('token');
const form = document.getElementById('reset-form');
const messageEl = document.getElementById('reset-message');
const newPasswordInput = document.getElementById('new-password');
const confirmPasswordInput = document.getElementById('confirm-password');

function wirePasswordToggle(toggleId, inputEl) {
    const toggle = document.getElementById(toggleId);
    const eyeIcon = toggle.querySelector('.feather-eye');
    const eyeOffIcon = toggle.querySelector('.feather-eye-off');

    toggle.addEventListener('click', () => {
        const isHidden = inputEl.type === 'password';
        inputEl.type = isHidden ? 'text' : 'password';
        eyeIcon.style.display = isHidden ? 'none' : 'block';
        eyeOffIcon.style.display = isHidden ? 'block' : 'none';
    });
}

wirePasswordToggle('toggle-new-password-visibility', newPasswordInput);
wirePasswordToggle('toggle-confirm-password-visibility', confirmPasswordInput);

if (!token) {
    messageEl.className = 'erreur';
    messageEl.textContent = 'Lien invalide : aucun jeton de réinitialisation trouvé.';
    form.querySelector('button[type="submit"]').disabled = true;
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    messageEl.textContent = '';

    if (newPasswordInput.value !== confirmPasswordInput.value) {
        messageEl.className = 'erreur';
        messageEl.textContent = 'Les mots de passe ne correspondent pas.';
        return;
    }

    const res = await fetch(`${API}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPasswordInput.value }),
    });
    const data = await res.json();

    if (res.ok) {
        messageEl.className = 'succes';
        messageEl.textContent = 'Mot de passe réinitialisé ! Redirection vers la connexion...';
        setTimeout(() => window.location.href = 'login.html', 1500);
    } else {
        messageEl.className = 'erreur';
        messageEl.textContent = data.detail || 'Erreur lors de la réinitialisation.';
    }
});
