const API = '';
const token = () => localStorage.getItem('miabewifi_token');
const isLoginPage = document.getElementById('login-form') !== null;

// --- Page de connexion / inscription ---
if (isLoginPage) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleBtn = document.getElementById('toggle-form');
    const formTitle = document.getElementById('form-title');
    const message = document.getElementById('message');

    toggleBtn.addEventListener('click', () => {
        const showingLogin = loginForm.style.display !== 'none';
        loginForm.style.display = showingLogin ? 'none' : 'block';
        registerForm.style.display = showingLogin ? 'block' : 'none';
        formTitle.textContent = showingLogin ? 'Créer un compte' : 'Connexion';
        toggleBtn.textContent = showingLogin ? 'Se connecter à la place' : 'Créer un compte à la place';
        message.textContent = '';
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        message.textContent = '';
        const body = new URLSearchParams();
        body.append('username', document.getElementById('login-email').value);
        body.append('password', document.getElementById('login-password').value);

        const res = await fetch(`${API}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        });
        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('miabewifi_token', data.access_token);
            window.location.href = 'dashboard.html';
        } else {
            message.className = 'erreur';
            message.textContent = data.detail || 'Erreur de connexion.';
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        message.textContent = '';

        const res = await fetch(`${API}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nom: document.getElementById('register-nom').value,
                email: document.getElementById('register-email').value,
                password: document.getElementById('register-password').value,
            }),
        });
        const data = await res.json();

        if (res.ok) {
            message.className = 'succes';
            message.textContent = 'Compte créé ! Tu peux te connecter.';
            toggleBtn.click();
        } else {
            message.className = 'erreur';
            message.textContent = data.detail || 'Erreur lors de la création du compte.';
        }
    });
}

// --- Tableau de bord ---
if (!isLoginPage && document.getElementById('routers-list')) {
    if (!token()) {
        window.location.href = 'login.html';
    }

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('miabewifi_token');
        window.location.href = 'login.html';
    });

    async function apiFetch(url, options = {}) {
        const res = await fetch(url, {
            ...options,
            headers: {
                ...(options.headers || {}),
                Authorization: `Bearer ${token()}`,
            },
        });
        if (res.status === 401) {
            localStorage.removeItem('miabewifi_token');
            window.location.href = 'login.html';
            return null;
        }
        return res;
    }

    async function chargerSolde() {
        const res = await apiFetch('/wallet/solde');
        if (!res) return;
        const data = await res.json();
        document.getElementById('solde-affiche').textContent = `${data.solde} FCFA`;
    }

    async function chargerRouteurs() {
        const res = await apiFetch('/routers/');
        if (!res) return;
        const routeurs = await res.json();
        const container = document.getElementById('routers-list');

        if (routeurs.length === 0) {
            container.innerHTML = '<p>Aucun routeur pour le moment.</p>';
            return;
        }

        container.innerHTML = routeurs.map(r => {
            const now = new Date();
            const trialActif = r.trial_expires_at && new Date(r.trial_expires_at) > now;
            const abonnementActif = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
            const actif = trialActif || abonnementActif;

            return `
        <div class="router-item">
          <strong>${r.nom}</strong>
          <span class="badge ${actif ? 'actif' : 'inactif'}">${actif ? 'Actif' : 'Expiré'}</span>
          <p>IP tunnel: ${r.wireguard_ip || 'N/A'}</p>
          <p>Ports — Winbox: ${r.ports.find(p => p.service_type === 'winbox')?.public_port || '-'} |
             WebFig: ${r.ports.find(p => p.service_type === 'webfig')?.public_port || '-'} |
             SSH: ${r.ports.find(p => p.service_type === 'ssh')?.public_port || '-'}</p>
          ${trialActif ? `<p>Essai jusqu'au: ${new Date(r.trial_expires_at).toLocaleString()}</p>` : ''}
          ${abonnementActif ? `<p>Abonnement jusqu'au: ${new Date(r.subscription_expires_at).toLocaleString()}</p>` : ''}
          <button class="secondary" onclick="voirConfig(${r.id})">Voir script de config</button>
          <button class="secondary" onclick="activerPack(${r.id})">Activer un pack</button>
          <button class="danger" onclick="supprimerRouteur(${r.id})">Supprimer</button>
          <div id="config-${r.id}"></div>
        </div>
      `;
        }).join('');
    }

    window.voirConfig = async (id) => {
        const res = await apiFetch(`/routers/${id}/regenerate`, { method: 'POST' });
        if (!res) return;
        const data = await res.json();
        document.getElementById(`config-${id}`).innerHTML = `<pre>${data.config_script}</pre>`;
    };

    window.activerPack = async (id) => {
        const packId = prompt('Quel pack ? (7j, 30j, 90j)');
        if (!packId) return;
        const res = await apiFetch(`/routers/${id}/activer-pack`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pack_id: packId }),
        });
        if (!res) return;
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            chargerSolde();
            chargerRouteurs();
        } else {
            alert(data.detail);
        }
    };

    window.supprimerRouteur = async (id) => {
        if (!confirm('Supprimer ce routeur ?')) return;
        const res = await apiFetch(`/routers/${id}`, { method: 'DELETE' });
        if (!res) return;
        chargerRouteurs();
    };

    document.getElementById('create-router-btn').addEventListener('click', async () => {
        const nom = document.getElementById('new-router-nom').value;
        const messageEl = document.getElementById('create-router-message');
        if (!nom) return;

        const res = await apiFetch('/routers/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom }),
        });
        if (!res) return;
        const data = await res.json();

        if (res.ok) {
            messageEl.className = 'succes';
            messageEl.textContent = 'Routeur créé !';
            document.getElementById('new-router-nom').value = '';
            chargerRouteurs();
        } else {
            messageEl.className = 'erreur';
            messageEl.textContent = data.detail || 'Erreur.';
        }
    });

    document.getElementById('recharge-btn').addEventListener('click', async () => {
        const messageEl = document.getElementById('recharge-message');
        const res = await apiFetch('/wallet/recharger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: document.getElementById('recharge-phone').value,
                network: document.getElementById('recharge-network').value,
                montant: parseFloat(document.getElementById('recharge-montant').value),
            }),
        });
        if (!res) return;
        const data = await res.json();

        if (res.ok) {
            messageEl.className = 'succes';
            messageEl.textContent = data.message;
        } else {
            messageEl.className = 'erreur';
            messageEl.textContent = data.detail || 'Erreur.';
        }
    });

    chargerSolde();
    chargerRouteurs();
}