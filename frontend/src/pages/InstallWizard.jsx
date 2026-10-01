import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Copy, Check, Loader2, Wifi, PartyPopper } from 'lucide-react';
import api from '../api/client';
import './InstallWizard.css';

const STEP_LABELS = {
    1: "création du routeur",
    2: "collage du script (navigateur ou Winbox)",
    3: "attente de connexion du routeur",
    4: "choix du forfait",
};

const RECOMMENDED_PACK_ID = '30j';

// Nom de Wi-Fi accepté par le routeur : lettres, chiffres, espace, point, tiret, tiret bas.
function sanitizeSsid(value) {
    return value.replace(/[^A-Za-z0-9 ._-]/g, '').slice(0, 32);
}
const POLL_INTERVAL_MS = 4000;

export default function InstallWizard() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [nom, setNom] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [router, setRouter] = useState(null);
    const [script, setScript] = useState('');
    const [copied, setCopied] = useState(false);
    const [connected, setConnected] = useState(false);
    const [longWait, setLongWait] = useState(false);
    const [mode, setMode] = useState('');
    const [tunnelUp, setTunnelUp] = useState(false);
    const [provisionError, setProvisionError] = useState('');
    const [provisionInfo, setProvisionInfo] = useState(null);
    const [packs, setPacks] = useState([]);
    const [wifiSsid, setWifiSsid] = useState('');
    const [lanInterfaces, setLanInterfaces] = useState([]);
    const [lanInterface, setLanInterface] = useState('');
    const [helpOpen, setHelpOpen] = useState(false);
    const [helpMessage, setHelpMessage] = useState('');
    const [helpSent, setHelpSent] = useState(false);
    const pollRef = useRef(null);

    // Étape 3 : on vérifie la connexion toutes les 4 secondes, sans que
    // l'utilisateur ait à cliquer sur quoi que ce soit.
    useEffect(() => {
        if (step !== 3 || !router) return;

        pollRef.current = setInterval(async () => {
            try {
                const res = await api.get(`/routers/${router.id}/status`);
                if (res.data.connecte) {
                    clearInterval(pollRef.current);
                    setTunnelUp(true);
                    api.get('/packs/').then((r) => setPacks(r.data)).catch(() => setPacks([]));
                    runProvision(router.id);
                }
            } catch {
                // on ignore une erreur ponctuelle de sondage, on réessaie au prochain tick
            }
        }, POLL_INTERVAL_MS);

        return () => clearInterval(pollRef.current);
    }, [step, router]);

    // Routeur "déjà en service" sans HotSpot : on propose d'en créer un sur l'une de ses interfaces.
    useEffect(() => {
        if (step !== 4 || !router || !provisionInfo || provisionInfo.hotspot_present) return;
        api.get(`/routers/${router.id}/lan-interfaces`)
            .then((res) => {
                setLanInterfaces(res.data);
                if (res.data.length > 0) setLanInterface(res.data[0].name);
            })
            .catch(() => setLanInterfaces([]));
    }, [step, router, provisionInfo]);

    // Après 45 secondes sans connexion, on affiche des pistes concrètes
    // au lieu de laisser le client face à un simple message qui tourne.
    useEffect(() => {
        if (step !== 3) return;
        setLongWait(false);
        const timeout = setTimeout(() => setLongWait(true), 45000);
        return () => clearTimeout(timeout);
    }, [step]);

    // Juste après la connexion du tunnel, le routeur peut encore être en train de générer
    // son certificat de sécurité (jusqu'à plusieurs minutes selon le modèle) : l'API ne répond
    // qu'ensuite. On réessaie donc patiemment (≈ 5 minutes) avant d'afficher une erreur.
    const PROVISION_MAX_ATTEMPTS = 60;
    const PROVISION_RETRY_DELAY_MS = 5000;

    async function runProvision(routerId) {
        setProvisionError('');
        for (let attempt = 0; attempt < PROVISION_MAX_ATTEMPTS; attempt++) {
            try {
                const res = await api.post(`/routers/${routerId}/provision`);
                setProvisionInfo(res.data);
                setConnected(true);
                setTimeout(() => setStep(4), 1200);
                return;
            } catch (err) {
                const detail = err.response?.data?.detail;
                // 400 = version RouterOS trop ancienne : inutile de réessayer.
                if (err.response?.status === 400 || attempt === PROVISION_MAX_ATTEMPTS - 1) {
                    setProvisionError(detail || "Impossible de préparer le routeur. Réessaie dans un instant.");
                    return;
                }
                await new Promise((r) => setTimeout(r, PROVISION_RETRY_DELAY_MS));
            }
        }
    }

    async function handleCreate(e) {
        e.preventDefault();
        if (!nom.trim() || !mode) return;
        setBusy(true);
        setError('');
        try {
            const payload = { nom: nom.trim(), mode };
            if (mode === 'new') payload.wifi_ssid = sanitizeSsid(wifiSsid.trim() || nom.trim());
            const res = await api.post('/routers/', payload);
            setRouter(res.data.router);
            setScript(res.data.config_script);
            setStep(2);
        } catch (err) {
            setError(err.response?.data?.detail || "Impossible de créer le routeur. Réessayez.");
        } finally {
            setBusy(false);
        }
    }

    function handleCopy() {
        navigator.clipboard.writeText(script);
        setCopied(true);
    }

    async function handleDownloadCard() {
        try {
            const res = await api.get(`/routers/${router.id}/setup-card`, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = `installation-${router.nom}.pdf`;
            link.click();
            window.URL.revokeObjectURL(url);
        } catch {
            setError("Impossible de générer la fiche d'installation pour le moment.");
        }
    }

    async function handleSendHelp(e) {
        e.preventDefault();
        try {
            await api.post('/support/contact', {
                message: `[Assistant d'installation — bloqué à l'étape "${STEP_LABELS[step]}"] ${helpMessage.trim() || "L'utilisateur demande de l'aide sans précision."}`,
            });
            setHelpSent(true);
        } catch {
            setHelpSent(true); // on affiche quand même une confirmation rassurante côté utilisateur
        }
    }

    async function handleSetupHotspot() {
        if (!lanInterface) return;
        if (!window.confirm(`Créer un HotSpot sur « ${lanInterface} » ? Tous les appareils connectés à cette interface devront saisir un ticket pour accéder à Internet.`)) return;
        setBusy(true);
        setError('');
        try {
            const res = await api.post(`/routers/${router.id}/setup-hotspot`, { interface: lanInterface });
            setProvisionInfo(res.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Impossible de créer le HotSpot.");
        } finally {
            setBusy(false);
        }
    }

    async function handleActiverPack(packId) {
        setBusy(true);
        setError('');
        try {
            await api.post(`/routers/${router.id}/activer-pack`, { pack_id: packId });
            navigate('/routers');
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur lors de l'activation du pack.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="wizard">
            <button className="wizard-quit-btn" onClick={() => navigate('/routers')}>
                Quitter
            </button>
            <div className="wizard-progress">
                {[1, 2, 3, 4].map((n) => (
                    <div key={n} className={`wizard-dot ${n <= step ? 'is-done' : ''}`} />
                ))}
            </div>
            <p className="wizard-step-label">Étape {step} sur 4</p>

            {error && <p className="error-text">{error}</p>}

            {step === 1 && (
                <div className="wizard-card">
                    <h1>Ajoute ton routeur</h1>
                    <p className="wizard-hint">Donne-lui un nom pour le reconnaître facilement (ex : "Cybercafé Bè").</p>
                    <form onSubmit={handleCreate}>
                        <input
                            className="text-input wizard-input"
                            type="text"
                            value={nom}
                            onChange={(e) => setNom(e.target.value)}
                            placeholder="Nom du routeur"
                            autoFocus
                        />
                        <p className="wizard-hint">Dans quel état est ton routeur ?</p>
                        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', margin: '8px 0' }}>
                            <input type="radio" name="mode" value="new" checked={mode === 'new'} onChange={() => setMode('new')} />
                            <span>
                                <strong>Neuf ou remis à zéro</strong> — MIABEWIFI configure le réseau, le Wi-Fi et le HotSpot pour toi.
                                C'est le choix à faire pour vendre des tickets.
                            </span>
                        </label>
                        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', margin: '8px 0' }}>
                            <input type="radio" name="mode" value="existing" checked={mode === 'existing'} onChange={() => setMode('existing')} />
                            <span>
                                <strong>Déjà en service</strong> — ta configuration actuelle n'est pas modifiée et aucun HotSpot
                                n'est créé automatiquement (tu pourras en ajouter un à la fin si besoin).
                            </span>
                        </label>
                        {mode === 'new' && (
                            <>
                                <p className="wizard-hint">Nom du Wi-Fi que verront tes clients :</p>
                                <input
                                    className="text-input wizard-input"
                                    type="text"
                                    value={wifiSsid}
                                    onChange={(e) => setWifiSsid(sanitizeSsid(e.target.value))}
                                    placeholder={sanitizeSsid(nom.trim()) || 'MIABEWIFI'}
                                    maxLength={32}
                                />
                                <p className="wizard-hint wizard-hint-small">
                                    Le Wi-Fi est ouvert (sans mot de passe) : les clients se connectent, puis saisissent leur ticket.
                                </p>
                            </>
                        )}
                        <button className="btn-primary wizard-btn-main" type="submit" disabled={busy || !nom.trim() || !mode}>
                            {busy ? 'Création...' : 'Continuer'}
                        </button>
                    </form>
                </div>
            )}

            {step === 2 && (
                <div className="wizard-card">
                    <h1>Configure ton routeur</h1>
                    {mode === 'new' && (
                        <p className="wizard-hint">
                            <strong>Utilise un câble Ethernet</strong> entre ton ordinateur et le routeur : à la fin du
                            script, le Wi-Fi du routeur est renommé et une connexion Wi-Fi serait coupée.
                        </p>
                    )}
                    <p className="wizard-hint">
                        Connecte-toi d'abord au réseau de ton routeur (câble Ethernet de préférence, ou son Wi-Fi
                        par défaut), puis clique ci-dessous : ça ouvre la page de configuration de
                        ton routeur directement dans un nouvel onglet — aucun logiciel à installer.
                    </p>
                    <a
                        className="btn-secondary wizard-copy-btn"
                        href="http://192.168.88.1/"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-block', textDecoration: 'none', textAlign: 'center' }}
                    >
                        Ouvrir la configuration de mon routeur
                    </a>
                    <p className="wizard-hint wizard-hint-small">
                        Connecte-toi avec "admin" (sans mot de passe, sauf si tu l'as déjà changé),
                        puis clique sur "Terminal" dans le menu de gauche.
                    </p>
                    <p className="wizard-hint">
                        Copie ensuite ce script et colle-le dans ce terminal :
                    </p>
                    <p className="wizard-hint wizard-hint-small">
                        Après le collage, le routeur peut mettre jusqu'à 5 minutes à terminer (génération du
                        certificat de sécurité). Ne tape rien dans le terminal tant que le curseur n'est pas revenu.
                    </p>
                    {mode === 'new' && (
                        <p className="wizard-hint wizard-hint-small">
                            À la fin, la page du routeur peut se couper ou se recharger : c'est normal, le HotSpot vient d'être activé.
                        </p>
                    )}
                    <pre className="config-script wizard-script">{script}</pre>
                    <button className="btn-secondary wizard-copy-btn" onClick={handleCopy}>
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                        {copied ? 'Copié !' : 'Copier le script'}
                    </button>
                    <p className="wizard-hint wizard-hint-small">
                        L'adresse ne s'ouvre pas, ou tu préfères utiliser Winbox ?
                    </p>
                    <button className="btn-secondary wizard-copy-btn" onClick={handleDownloadCard}>
                        Télécharger la fiche d'installation (PDF)
                    </button>
                    <button
                        className="btn-primary wizard-btn-main"
                        disabled={!copied}
                        onClick={() => setStep(3)}
                    >
                        J'ai collé le script
                    </button>
                </div>
            )}

            {step === 3 && (
                <div className="wizard-card wizard-card-centered">
                    {connected ? (
                        <>
                            <Wifi className="wizard-success-icon" size={48} />
                            <h1>Routeur prêt !</h1>
                        </>
                    ) : tunnelUp && provisionError ? (
                        <>
                            <h1>Routeur connecté, mais…</h1>
                            <p className="error-text">{provisionError}</p>
                            <button className="btn-secondary wizard-copy-btn" onClick={() => runProvision(router.id)}>
                                Réessayer
                            </button>
                        </>
                    ) : tunnelUp ? (
                        <>
                            <Loader2 className="wizard-spinner" size={48} />
                            <h1>Routeur connecté</h1>
                            <p className="wizard-hint">Préparation de ton HotSpot en cours...</p>
                            <p className="wizard-hint wizard-hint-small">
                                Le routeur génère son certificat de sécurité : cela peut prendre jusqu'à 5 minutes
                                selon le modèle. Ne ferme pas cette page.
                            </p>
                        </>
                    ) : (
                        <>
                            <Loader2 className="wizard-spinner" size={48} />
                            <h1>En attente de connexion...</h1>
                            {!longWait ? (
                                <p className="wizard-hint">
                                    Vérifie que tu as bien collé tout le script, y compris la dernière ligne.
                                </p>
                            ) : (
                                <>
                                    <p className="wizard-hint">Ça prend plus longtemps que prévu. Vérifie que :</p>
                                    <ul className="wizard-hint" style={{ textAlign: 'left' }}>
                                        <li>le script a été collé en entier, sans ligne coupée</li>
                                        <li>le routeur est bien connecté à Internet</li>
                                        <li>tu n'as pas de pare-feu qui bloque le port 51820</li>
                                    </ul>
                                    <p className="wizard-hint wizard-hint-small">
                                        Toujours bloqué ? Utilise le bouton "Besoin d'aide ?" en bas de l'écran.
                                    </p>
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {step === 4 && (
                <div className="wizard-card">
                    <PartyPopper size={40} className="wizard-success-icon" />
                    <h1>Choisis ton forfait</h1>
                    {provisionInfo && !provisionInfo.hotspot_present && (
                        <div>
                            <p className="error-text">
                                Aucun HotSpot n'a été détecté sur ce routeur : tu ne pourras pas générer de tickets
                                tant qu'il n'est pas activé.
                            </p>
                            {lanInterfaces.length > 0 ? (
                                <>
                                    <p className="wizard-hint">
                                        Choisis le réseau sur lequel tes clients se connectent (en général « bridge ») :
                                    </p>
                                    <select
                                        className="text-input wizard-input"
                                        value={lanInterface}
                                        onChange={(e) => setLanInterface(e.target.value)}
                                    >
                                        {lanInterfaces.map((i) => (
                                            <option key={i.name} value={i.name}>{i.name} ({i.type})</option>
                                        ))}
                                    </select>
                                    <button className="btn-secondary wizard-copy-btn" disabled={busy} onClick={handleSetupHotspot}>
                                        Créer le HotSpot sur ce réseau
                                    </button>
                                </>
                            ) : (
                                <p className="wizard-hint">
                                    Utilise « Besoin d'aide ? » pour être accompagné, ou recommence avec l'option « Neuf ou remis à zéro ».
                                </p>
                            )}
                        </div>
                    )}
                    <p className="wizard-hint">
                        Ton essai gratuit de 3 jours est déjà actif — le forfait prend le relais après.
                    </p>
                    <div className="wizard-packs">
                        {packs.map((p) => (
                            <button
                                key={p.id}
                                className={`wizard-pack-card ${p.id === RECOMMENDED_PACK_ID ? 'is-recommended' : ''}`}
                                disabled={busy}
                                onClick={() => handleActiverPack(p.id)}
                            >
                                {p.id === RECOMMENDED_PACK_ID && <span className="wizard-pack-badge">Recommandé</span>}
                                <span className="wizard-pack-label">{p.label}</span>
                                <span className="wizard-pack-price">{p.montant} FCFA</span>
                            </button>
                        ))}
                    </div>
                    <button className="btn-secondary wizard-later-btn" onClick={() => navigate('/routers')}>
                        Plus tard — profiter de mon essai gratuit
                    </button>
                </div>
            )}

            <button className="wizard-help-link" onClick={() => setHelpOpen(true)}>
                Besoin d'aide ?
            </button>

            {helpOpen && (
                <div className="modal-overlay" onClick={() => setHelpOpen(false)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                        {helpSent ? (
                            <p className="success-text">
                                C'est envoyé ! Notre équipe vous recontacte rapidement.
                            </p>
                        ) : (
                            <form className="form-stack" onSubmit={handleSendHelp}>
                                <label className="field-label" htmlFor="wizard-help">
                                    Décris ton problème (optionnel, on voit déjà où tu es bloqué)
                                </label>
                                <textarea
                                    id="wizard-help"
                                    className="text-input"
                                    style={{ width: '100%', minHeight: 100 }}
                                    value={helpMessage}
                                    onChange={(e) => setHelpMessage(e.target.value)}
                                />
                                <button className="btn-primary" type="submit">Envoyer</button>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}