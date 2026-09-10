const API = '';
const token = () => localStorage.getItem('miabewifi_token') || sessionStorage.getItem('miabewifi_token');
const isLoginPage = document.getElementById('login-form') !== null;

// --- Page de connexion / inscription ---
if (isLoginPage) {
    // Si une session existe déjà (token en localStorage via "Rester connecté",
    // ou en sessionStorage pour l'onglet en cours), on saute directement au tableau de bord.
    if (token()) {
        window.location.href = 'dashboard.html';
    }

    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleBtn = document.getElementById('toggle-form');
    const footerToggle = document.getElementById('footer-toggle');
    const heading = document.getElementById('form-heading');
    const subtitle = document.getElementById('form-subtitle');
    const message = document.getElementById('message');

    if (typeof feather !== 'undefined') feather.replace();

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

    wirePasswordToggle('toggle-password-visibility', document.getElementById('login-password'));
    wirePasswordToggle('toggle-register-password-visibility', document.getElementById('register-password'));

    // --- Mot de passe oublié ---
    const forgotLink = document.getElementById('forgot-password-link');
    const forgotModal = document.getElementById('forgot-modal');
    const forgotModalClose = document.getElementById('forgot-modal-close');
    const forgotEmailInput = document.getElementById('forgot-email');
    const forgotSubmitBtn = document.getElementById('forgot-submit-btn');
    const forgotMessage = document.getElementById('forgot-message');

    forgotLink.addEventListener('click', (e) => {
        e.preventDefault();
        forgotMessage.textContent = '';
        forgotMessage.className = '';
        forgotEmailInput.value = '';
        forgotModal.style.display = 'flex';
    });

    forgotModalClose.addEventListener('click', () => {
        forgotModal.style.display = 'none';
    });

    forgotModal.addEventListener('click', (e) => {
        if (e.target === forgotModal) forgotModal.style.display = 'none';
    });

    forgotSubmitBtn.addEventListener('click', async () => {
        const email = forgotEmailInput.value.trim();
        if (!email) return;

        forgotSubmitBtn.disabled = true;
        forgotMessage.textContent = '';

        try {
            const res = await fetch(`${API}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();
            forgotMessage.className = 'succes';
            forgotMessage.textContent = data.message || "Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé.";
        } catch (err) {
            forgotMessage.className = 'erreur';
            forgotMessage.textContent = 'Erreur de connexion au serveur.';
        } finally {
            forgotSubmitBtn.disabled = false;
        }
    });

    toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const showingLogin = loginForm.style.display !== 'none';
        loginForm.style.display = showingLogin ? 'none' : 'block';
        registerForm.style.display = showingLogin ? 'block' : 'none';
        heading.textContent = showingLogin ? 'Créer un compte' : 'Bon retour';
        subtitle.textContent = showingLogin ? 'Commencez à piloter vos routeurs en 1 minute.' : "Pilotez vos routeurs MikroTik depuis n'importe où.";
        footerToggle.innerHTML = showingLogin
            ? `Déjà un compte ? <a href="#" id="toggle-form">Se connecter →</a>`
            : `Pas encore de compte ? <a href="#" id="toggle-form">Créer un compte gratuitement →</a>`;
        document.getElementById('toggle-form').addEventListener('click', (ev) => { ev.preventDefault(); toggleBtn.click(); });
        message.textContent = '';
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        message.textContent = '';
        const body = new URLSearchParams();
        body.append('username', document.getElementById('login-email').value);
        body.append('password', document.getElementById('login-password').value);

        try {
            const res = await fetch(`${API}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body,
            });
            const data = await res.json();

            if (res.ok) {
                const remember = document.getElementById('remember-me').checked;
                const storage = remember ? localStorage : sessionStorage;
                storage.setItem('miabewifi_token', data.access_token);
                window.location.href = 'dashboard.html';
            } else {
                message.className = 'erreur';
                message.textContent = data.detail || 'Erreur de connexion.';
            }
        } catch (err) {
            message.className = 'erreur';
            message.textContent = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
            console.error('Erreur login:', err);
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        message.textContent = '';

        try {
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
        } catch (err) {
            message.className = 'erreur';
            message.textContent = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
            console.error('Erreur register:', err);
        }
    });
}

// --- Navigation entre vues (tableau de bord + admin) ---
window.allerA = function (viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector(`.view[data-view="${viewName}"]`).classList.add('active');

    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    const activeLink = document.querySelector(`.nav-link[data-target="${viewName}"]`);
    if (activeLink) activeLink.classList.add('active');

    document.querySelector('.topbar .breadcrumb').innerHTML =
        `<strong>MIABEWIFI</strong> · ${document.querySelector(`.view[data-view="${viewName}"] h1`).textContent}`;

    localStorage.setItem('miabewifi_current_view', viewName);

    if (viewName === 'wallet') chargerTransactions();
};

// --- Tableau de bord (client + admin) ---
if (!isLoginPage && document.getElementById('routers-list')) {
    if (!token()) {
        window.location.href = 'login.html';
    }

    if (typeof feather !== 'undefined') feather.replace();

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('miabewifi_token');
        sessionStorage.removeItem('miabewifi_token');
        window.location.href = 'login.html';
    });

    // --- Menu mobile (sidebar en tiroir) ---
    const sidebarEl = document.querySelector('.sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const menuToggleBtn = document.getElementById('menu-toggle');

    const ouvrirSidebar = () => {
        sidebarEl.classList.add('open');
        sidebarOverlay.classList.add('active');
    };
    const fermerSidebar = () => {
        sidebarEl.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    };

    menuToggleBtn.addEventListener('click', () => {
        sidebarEl.classList.contains('open') ? fermerSidebar() : ouvrirSidebar();
    });
    sidebarOverlay.addEventListener('click', fermerSidebar);

    // Ferme le menu automatiquement après avoir choisi une section (mobile)
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 900) fermerSidebar();
        });
    });

    async function apiFetch(url, options = {}) {
        const res = await fetch(url, {
            ...options,
            headers: { ...(options.headers || {}), Authorization: `Bearer ${token()}` },
        });
        if (res.status === 401) {
            localStorage.removeItem('miabewifi_token');
            sessionStorage.removeItem('miabewifi_token');
            window.location.href = 'login.html';
            return null;
        }
        return res;
    }

    async function chargerUtilisateur() {
        const res = await apiFetch('/auth/me');
        if (!res) return;
        const data = await res.json();

        document.getElementById('user-name').textContent = data.nom;
        document.getElementById('greeting-name').textContent = data.nom;
        document.getElementById('user-avatar').textContent = data.nom.charAt(0).toUpperCase();

        document.getElementById('profile-nom').textContent = data.nom;
        document.getElementById('profile-email').textContent = data.email;
        document.getElementById('profile-date').textContent = new Date(data.created_at).toLocaleDateString();

        if (data.role === 'admin') {
            document.getElementById('admin-section').style.display = 'block';
            ['admin-link-1', 'admin-link-2', 'admin-link-3', 'admin-link-4'].forEach(id => {
                document.getElementById(id).style.display = 'flex';
            });
            chargerStats();
            chargerUsers();
            chargerAllRouters();
            chargerAllTx();
        }
    }

    async function chargerSolde() {
        const res = await apiFetch('/wallet/solde');
        if (!res) return;
        const data = await res.json();
        document.getElementById('solde-affiche').innerHTML = `${data.solde} <small>FCFA</small>`;
        document.getElementById('w-solde').innerHTML = `${data.solde} <small>FCFA</small>`;
        document.getElementById('solde-affiche-2').innerHTML = `${data.solde} <small>FCFA</small>`;
    }

    async function chargerRouteurs() {
        const res = await apiFetch('/routers/');
        if (!res) return;
        const routeurs = await res.json();
        const now = new Date();

        const actifs = routeurs.filter(r => {
            const trial = r.trial_expires_at && new Date(r.trial_expires_at) > now;
            const abo = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
            return trial || abo;
        });

        document.getElementById('routers-count').innerHTML = `${actifs.length}<small>/${routeurs.length}</small>`;
        document.getElementById('routers-count-text').textContent =
            routeurs.length === 0 ? 'Aucun routeur pour le moment' : `${actifs.length} routeur(s) actif(s) sur ${routeurs.length}`;
        document.getElementById('routers-status-count').textContent = routeurs.length;

        const dates = routeurs
            .map(r => r.subscription_expires_at ? new Date(r.subscription_expires_at) : null)
            .filter(d => d && d > now)
            .sort((a, b) => a - b);
        document.getElementById('next-deadline').textContent =
            dates.length > 0 ? dates[0].toLocaleDateString() : 'Aucune licence active';

        const dans7j = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
        const echeancesProches = routeurs.filter(r => {
            const d = r.subscription_expires_at ? new Date(r.subscription_expires_at) : null;
            return d && d > now && d <= dans7j;
        });
        document.getElementById('deadlines-count').textContent = echeancesProches.length;
        document.getElementById('deadlines-list').innerHTML = echeancesProches.length === 0
            ? `<p class="empty-hint">✓ Aucune licence n'expire dans les 7 prochains jours.</p>`
            : echeancesProches.map(r => `<p>⚠️ <strong>${r.nom}</strong> expire le ${new Date(r.subscription_expires_at).toLocaleDateString()}</p>`).join('');

        const aSurveiller = routeurs.filter(r => {
            const trial = r.trial_expires_at && new Date(r.trial_expires_at) > now;
            const abo = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
            return !trial && !abo;
        });
        document.getElementById('watch-count').textContent = aSurveiller.length;
        document.getElementById('watch-list').innerHTML = aSurveiller.length === 0
            ? `<p class="empty-hint">✓ Tous vos routeurs sont opérationnels.</p>`
            : aSurveiller.map(r => `<p>🔴 <strong>${r.nom}</strong> — accès expiré, pack à activer</p>`).join('');

        const html = routeurs.length === 0
            ? '<p class="empty-hint">Aucun routeur. Cliquez « Nouveau routeur » pour démarrer.</p>'
            : routeurs.map(r => {
                const trialActif = r.trial_expires_at && new Date(r.trial_expires_at) > now;
                const abonnementActif = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
                const actif = trialActif || abonnementActif;

                return `
            <div class="router-item" data-search="${r.nom.toLowerCase()}">
            
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

        document.getElementById('routers-list').innerHTML = html;
        document.getElementById('routers-list-preview').innerHTML = html;
        document.getElementById('routers-status-count-2').textContent = routeurs.length;
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

    document.getElementById('retrait-btn').addEventListener('click', async () => {
        const messageEl = document.getElementById('retrait-message');
        const montant = parseFloat(document.getElementById('retrait-montant').value);
        const phone = document.getElementById('retrait-phone').value;

        if (!phone || !montant || montant <= 0) {
            messageEl.className = 'erreur';
            messageEl.textContent = 'Renseigne un numéro et un montant valides.';
            return;
        }

        if (!confirm(`Confirmer le retrait de ${montant} FCFA vers le ${phone} ?`)) return;

        const btn = document.getElementById('retrait-btn');
        btn.disabled = true;
        messageEl.textContent = '';

        const res = await apiFetch('/wallet/retirer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: phone,
                network: document.getElementById('retrait-network').value,
                montant,
            }),
        });
        btn.disabled = false;
        if (!res) return;
        const data = await res.json();

        if (res.ok) {
            messageEl.className = 'succes';
            messageEl.textContent = data.message;
            document.getElementById('retrait-montant').value = '';
            document.getElementById('retrait-phone').value = '';
            chargerSolde();
            chargerTransactions();
        } else {
            messageEl.className = 'erreur';
            messageEl.textContent = data.detail || 'Erreur.';
        }
    });

    function libelleTransaction(t) {
        if (t.type === 'recharge') return { label: '↓ Recharge', sign: '+', color: '#16a34a' };
        if (t.type === 'retrait') return { label: '↑ Retrait', sign: '-', color: '#dc2626' };
        return { label: '↑ Activation pack', sign: '-', color: '#dc2626' };
    }

    async function chargerTransactions() {
        const res = await apiFetch('/wallet/transactions');
        if (!res) return;
        const transactions = await res.json();

        const now = new Date();
        const il30j = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const recentes = transactions.filter(t => new Date(t.created_at) > il30j);

        const recharges = recentes.filter(t => t.type === 'recharge' && t.statut === 'confirme');
        const debits = recentes.filter(t => t.type === 'debit');

        const totalRecharge = recharges.reduce((s, t) => s + t.montant, 0);
        const totalDebit = debits.reduce((s, t) => s + t.montant, 0);
        const fraisEstimes = Math.round(totalRecharge * 0.035);

        document.getElementById('w-recharge-30j').innerHTML = `+${totalRecharge} <small>FCFA</small>`;
        document.getElementById('w-recharge-count').textContent = `${recharges.length} recharge(s)`;
        document.getElementById('w-debit-30j').innerHTML = `-${totalDebit} <small>FCFA</small>`;
        document.getElementById('w-debit-count').textContent = `${debits.length} licence(s) activée(s)`;
        document.getElementById('w-frais-30j').innerHTML = `~${fraisEstimes} <small>FCFA</small>`;

        document.getElementById('tx-count-label').textContent = `${transactions.length} sur ${transactions.length} récentes`;

        const listEl = document.getElementById('transactions-list');
        if (transactions.length === 0) {
            listEl.innerHTML = `
        <div style="text-align:center; padding:50px 0;">
          <div style="width:56px;height:56px;background:#fce7f3;border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:22px;">💳</div>
          <p style="font-weight:700; margin:0 0 4px;">Aucune transaction pour l'instant</p>
          <p class="sub-text">Rechargez votre portefeuille pour démarrer.</p>
        </div>`;
            return;
        }

        listEl.innerHTML = transactions.map(t => {
            const info = libelleTransaction(t);
            return `
      <div class="router-item" style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong>${info.label}</strong>
          <span class="badge ${t.statut === 'confirme' ? 'actif' : 'inactif'}">${t.statut}</span>
          <p class="sub-text">${t.methode} · ${new Date(t.created_at).toLocaleString()}</p>
        </div>
        <strong style="color:${info.color};">
          ${info.sign}${t.montant} FCFA
        </strong>
      </div>
    `;
        }).join('');

        window._transactionsCache = transactions;
    }

    document.getElementById('export-csv-btn').addEventListener('click', () => {
        const transactions = window._transactionsCache || [];
        if (transactions.length === 0) return;
        const header = 'Type,Montant,Methode,Statut,Date\n';
        const rows = transactions.map(t => `${t.type},${t.montant},${t.methode},${t.statut},${t.created_at}`).join('\n');
        const blob = new Blob([header + rows], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'transactions_miabewifi.csv';
        a.click();
    });

    let packSelectionne = null;
    let soldeActuel = 0;

    window.ouvrirModalPacks = async () => {
        document.getElementById('packs-modal').style.display = 'flex';
        retourListePacks();

        const [packsRes, soldeRes] = await Promise.all([
            apiFetch('/packs/'),
            apiFetch('/wallet/solde'),
        ]);
        if (!packsRes || !soldeRes) return;

        const packs = await packsRes.json();
        const solde = await soldeRes.json();
        soldeActuel = solde.solde;

        document.getElementById('packs-step-list').innerHTML = packs.map(p => `
      <div class="router-item">
        <strong>${p.label}</strong>
        <p style="font-size:20px; font-weight:800; margin:6px 0;">${p.montant} FCFA</p>
        <button onclick='choisirPack(${JSON.stringify(p)})'>Souscrire</button>
      </div>
    `).join('');
    };

    window.fermerModalPacks = () => {
        document.getElementById('packs-modal').style.display = 'none';
    };

    window.retourListePacks = () => {
        document.getElementById('packs-step-list').style.display = 'block';
        document.getElementById('packs-step-router').style.display = 'none';
        document.getElementById('packs-step-recharge').style.display = 'none';
    };

    window.choisirPack = async (pack) => {
        packSelectionne = pack;

        const res = await apiFetch('/routers/');
        if (!res) return;
        const routeurs = await res.json();

        if (routeurs.length === 0) {
            alert('Créez d\'abord un routeur avant d\'activer un pack.');
            return;
        }

        document.getElementById('pack-selectionne-label').textContent = `${pack.label} — ${pack.montant} FCFA`;
        document.getElementById('pack-router-select').innerHTML = routeurs.map(r => `<option value="${r.id}">${r.nom}</option>`).join('');

        document.getElementById('packs-step-list').style.display = 'none';
        document.getElementById('packs-step-router').style.display = 'block';
    };

    window.confirmerActivation = async () => {
        const routerId = document.getElementById('pack-router-select').value;
        const messageEl = document.getElementById('pack-activation-message');

        if (soldeActuel < packSelectionne.montant) {
            document.getElementById('packs-step-router').style.display = 'none';
            document.getElementById('packs-step-recharge').style.display = 'block';
            return;
        }

        const res = await apiFetch(`/routers/${routerId}/activer-pack`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pack_id: packSelectionne.id }),
        });
        if (!res) return;
        const data = await res.json();

        if (res.ok) {
            messageEl.className = 'succes';
            messageEl.textContent = data.message;
            chargerSolde();
            chargerRouteurs();
            setTimeout(fermerModalPacks, 1200);
        } else {
            if (data.detail && data.detail.includes('Solde insuffisant')) {
                document.getElementById('packs-step-router').style.display = 'none';
                document.getElementById('packs-step-recharge').style.display = 'block';
            } else {
                messageEl.className = 'erreur';
                messageEl.textContent = data.detail || 'Erreur.';
            }
        }
    };

    window.rechargerDepuisModal = async () => {
        const messageEl = document.getElementById('modal-recharge-message');
        const res = await apiFetch('/wallet/recharger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: document.getElementById('modal-recharge-phone').value,
                network: document.getElementById('modal-recharge-network').value,
                montant: parseFloat(document.getElementById('modal-recharge-montant').value),
            }),
        });
        if (!res) return;
        const data = await res.json();

        if (res.ok) {
            messageEl.className = 'succes';
            messageEl.textContent = data.message + ' Une fois confirmé, réessayez l\'activation.';
        } else {
            messageEl.className = 'erreur';
            messageEl.textContent = data.detail || 'Erreur.';
        }
    };

    // --- Fonctions Admin ---
    async function chargerStats() {
        const res = await apiFetch('/admin/stats');
        if (!res) return;
        const s = await res.json();
        document.getElementById('s-users').textContent = s.total_users;
        document.getElementById('s-routers').innerHTML = `${s.routers_actifs}<small>/${s.total_routers}</small>`;
        document.getElementById('s-revenus-30j').innerHTML = `${s.revenus_30j} <small>FCFA</small>`;
        document.getElementById('s-revenus-total').innerHTML = `${s.revenus_total} <small>FCFA</small>`;
    }

    async function chargerUsers() {
        const res = await apiFetch('/admin/users');
        if (!res) return;
        const users = await res.json();
        document.getElementById('users-list').innerHTML = `
      <div class="table-scroll">
      <table class="admin-table">
        <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Solde</th><th>Routeurs</th><th>Inscrit le</th></tr></thead>
        <tbody>
          ${users.map(u => `
            <tr data-search="${u.nom.toLowerCase()} ${u.email.toLowerCase()}">
              <td><strong>${u.nom}</strong></td>
              <td>${u.email}</td>
              <td><span class="role-pill ${u.role}">${u.role}</span></td>
              <td>${u.solde} FCFA</td>
              <td>${u.nb_routers}</td>
              <td>${new Date(u.created_at).toLocaleDateString()}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      </div>`;
    }

    async function chargerAllRouters() {
        const res = await apiFetch('/admin/routers');
        if (!res) return;
        const routers = await res.json();
        document.getElementById('allrouters-list').innerHTML = `
      <div class="table-scroll">
      <table class="admin-table">
        <thead><tr><th>Nom</th><th>Propriétaire</th><th>IP Tunnel</th><th>Statut</th><th>Connecté</th><th>Créé le</th></tr></thead>
        <tbody>
          ${routers.map(r => `
            <tr data-search="${r.nom.toLowerCase()} ${r.proprietaire.toLowerCase()} ${r.proprietaire_email.toLowerCase()}">
              <td><strong>${r.nom}</strong></td>
              <td>${r.proprietaire}<br><span class="sub-text">${r.proprietaire_email}</span></td>
              <td>${r.wireguard_ip || '-'}</td>
              <td><span class="badge ${r.actif ? 'actif' : 'inactif'}">${r.actif ? 'Actif' : 'Expiré'}</span></td>
              <td>${r.is_connected ? '🟢 Oui' : '⚪ Non'}</td>
              <td>${new Date(r.created_at).toLocaleDateString()}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      </div>`;
    }

    async function chargerAllTx() {
        const res = await apiFetch('/admin/transactions');
        if (!res) return;
        const txs = await res.json();
        document.getElementById('alltx-list').innerHTML = `
      <div class="table-scroll">
      <table class="admin-table">
        <thead><tr><th>Utilisateur</th><th>Type</th><th>Montant</th><th>Méthode</th><th>Statut</th><th>Date</th></tr></thead>
        <tbody>
          ${txs.map(t => {
            const info = libelleTransaction(t);
            return `
            <tr data-search="${t.user_nom.toLowerCase()} ${t.methode.toLowerCase()} ${t.type.toLowerCase()}">
              <td>${t.user_nom}</td>
              <td>${info.label}</td>
              <td style="color:${info.color};">
                ${info.sign}${t.montant} FCFA
              </td>
              <td>${t.methode}</td>
              <td><span class="badge ${t.statut === 'confirme' ? 'actif' : 'inactif'}">${t.statut}</span></td>
              <td>${new Date(t.created_at).toLocaleString()}</td>
            </tr>
          `;
          }).join('')}
        </tbody>
      </table>
      </div>`;
    }

    // --- Recherche globale (filtre la vue active) ---
    document.getElementById('search-input').addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        const vueActive = document.querySelector('.view.active');
        if (!vueActive) return;

        const items = vueActive.querySelectorAll('[data-search]');
        let visibleCount = 0;

        items.forEach(item => {
            const match = item.getAttribute('data-search').includes(query);
            const isRow = item.tagName === 'TR';
            item.style.display = match ? (isRow ? 'table-row' : 'block') : 'none';
            if (match) visibleCount++;
        });
    });

    // Sur mobile : la barre de recherche est un simple bouton rond qui s'élargit au clic
    const searchBar = document.getElementById('search-bar');
    const searchInputEl = document.getElementById('search-input');

    searchBar.addEventListener('click', () => {
        if (window.innerWidth <= 640 && !searchBar.classList.contains('expanded')) {
            searchBar.classList.add('expanded');
            searchInputEl.focus();
        }
    });

    searchInputEl.addEventListener('blur', () => {
        if (window.innerWidth <= 640 && searchInputEl.value.trim() === '') {
            searchBar.classList.remove('expanded');
        }
    });

    // Vide le champ de recherche à chaque changement de vue
    const allerAOriginal = window.allerA;
    window.allerA = function (viewName) {
        allerAOriginal(viewName);
        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.value = '';
        document.querySelectorAll('.view.active [data-search]').forEach(item => {
            item.style.display = item.tagName === 'TR' ? 'table-row' : 'block';
        });
    };

    async function chargerNotifications() {
        const res = await apiFetch('/notifications/');
        if (!res) return;
        const notifs = await res.json();

        const seen = JSON.parse(localStorage.getItem('miabewifi_notif_seen') || '[]');
        const nonVues = notifs.filter(n => !seen.includes(n.id));

        const badge = document.getElementById('notif-badge');
        if (nonVues.length > 0) {
            badge.textContent = nonVues.length > 9 ? '9+' : nonVues.length;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }

        const icons = { expiring: '⏳', expired: '🔴', info: 'ℹ️' };
        const listEl = document.getElementById('notif-list');

        listEl.innerHTML = notifs.length === 0
            ? `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:13px;">Aucune notification pour le moment.</div>`
            : notifs.map(n => `
          <div style="padding:12px 16px; border-bottom:1px solid var(--border); display:flex; gap:10px;">
            <span style="font-size:16px;">${icons[n.type] || '🔔'}</span>
            <div>
              <div style="font-weight:700; font-size:13px;">${n.title}</div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${n.message}</div>
            </div>
          </div>
        `).join('');

        window._notifCache = notifs;
    }

    document.getElementById('notif-bell').addEventListener('click', () => {
        const panel = document.getElementById('notif-panel');
        const showing = panel.style.display !== 'none';
        panel.style.display = showing ? 'none' : 'block';

        if (!showing) {
            const ids = (window._notifCache || []).map(n => n.id);
            localStorage.setItem('miabewifi_notif_seen', JSON.stringify(ids));
            document.getElementById('notif-badge').style.display = 'none';
        }
    });

    document.addEventListener('click', (e) => {
        const panel = document.getElementById('notif-panel');
        const bell = document.getElementById('notif-bell');
        if (panel.style.display === 'block' && !panel.contains(e.target) && !bell.contains(e.target)) {
            panel.style.display = 'none';
        }
    });

    setInterval(chargerNotifications, 60000); // rafraîchit toutes les 60 secondes

    // --- Initialisation ---
    chargerUtilisateur();
    chargerSolde();
    chargerRouteurs();
    chargerNotifications()

    const vueSauvegardee = localStorage.getItem('miabewifi_current_view') || 'dashboard';
    allerA(vueSauvegardee);
}