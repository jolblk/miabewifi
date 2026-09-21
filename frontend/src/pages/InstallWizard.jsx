import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Copy, Check, Loader2, Wifi, PartyPopper } from 'lucide-react';
import api from '../api/client';
import './InstallWizard.css';

const RECOMMENDED_PACK_ID = '30j';
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
    const [packs, setPacks] = useState([]);
    const pollRef = useRef(null);

    // Étape 3 : on vérifie la connexion toutes les 4 secondes, sans que
    // l'utilisateur ait à cliquer sur quoi que ce soit.
    useEffect(() => {
        if (step !== 3 || !router) return;

        pollRef.current = setInterval(async () => {
            try {
                const res = await api.get(`/routers/${router.id}/status`);
                if (res.data.actif) {
                    clearInterval(pollRef.current);
                    setConnected(true);
                    api.get('/packs/').then((r) => setPacks(r.data)).catch(() => setPacks([]));
                    setTimeout(() => setStep(4), 1200);
                }
            } catch {
                // on ignore une erreur ponctuelle de sondage, on réessaie au prochain tick
            }
        }, POLL_INTERVAL_MS);

        return () => clearInterval(pollRef.current);
    }, [step, router]);

    async function handleCreate(e) {
        e.preventDefault();
        if (!nom.trim()) return;
        setBusy(true);
        setError('');
        try {
            const res = await api.post('/routers/', { nom: nom.trim() });
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
                        <button className="btn-primary wizard-btn-main" type="submit" disabled={busy || !nom.trim()}>
                            {busy ? 'Création...' : 'Continuer'}
                        </button>
                    </form>
                </div>
            )}

            {step === 2 && (
                <div className="wizard-card">
                    <h1>Configure ton routeur</h1>
                    <p className="wizard-hint">
                        Copie ce script et colle-le dans le terminal Winbox de ton routeur MikroTik.
                    </p>
                    <pre className="config-script wizard-script">{script}</pre>
                    <button className="btn-secondary wizard-copy-btn" onClick={handleCopy}>
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                        {copied ? 'Copié !' : 'Copier le script'}
                    </button>
                    <p className="wizard-hint wizard-hint-small">
                        Besoin d'aide pour trouver le terminal dans Winbox ? Regarde le tutoriel vidéo (lien à venir).
                    </p>
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
                    {!connected ? (
                        <>
                            <Loader2 className="wizard-spinner" size={48} />
                            <h1>En attente de connexion...</h1>
                            <p className="wizard-hint">
                                Vérifie que tu as bien collé tout le script, y compris la dernière ligne.
                            </p>
                        </>
                    ) : (
                        <>
                            <Wifi className="wizard-success-icon" size={48} />
                            <h1>Routeur connecté !</h1>
                        </>
                    )}
                </div>
            )}

            {step === 4 && (
                <div className="wizard-card">
                    <PartyPopper size={40} className="wizard-success-icon" />
                    <h1>Choisis ton forfait</h1>
                    <p className="wizard-hint">Tu pourras en changer à tout moment depuis "Mes routeurs".</p>
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
                </div>
            )}
        </div>
    );
}