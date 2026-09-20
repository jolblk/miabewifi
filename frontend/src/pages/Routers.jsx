import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, Trash2, Zap, X, Copy } from 'lucide-react';
import { useRoutersData } from '../hooks/useRoutersData';
import { useSearch } from '../context/SearchContext';
import { stripAccents } from '../utils/normalizeText';
import './Routers.css';

function statutRouteur(r) {
    const now = new Date();
    const trial = r.trial_expires_at && new Date(r.trial_expires_at) > now;
    const abo = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
    if (abo) return { label: 'Abonné', cls: 'badge-success' };
    if (trial) return { label: 'Essai', cls: 'badge-warning' };
    return { label: 'Expiré', cls: 'badge-danger' };
}

export default function Routers() {
    const navigate = useNavigate();
    const { routers, packs, loading, error, createRouter, deleteRouter, regenerateRouter, activerPack } = useRoutersData();
    const { query } = useSearch();
    const normalizedQuery = stripAccents(query.trim());
    const filteredRouters = normalizedQuery
        ? routers.filter((r) => stripAccents(r.nom).includes(normalizedQuery))
        : routers;

    const [showForm, setShowForm] = useState(false);
    const [nom, setNom] = useState('');
    const [busy, setBusy] = useState(false);
    const [actionError, setActionError] = useState('');
    const [packRouterId, setPackRouterId] = useState(null);
    const [config, setConfig] = useState(null);

    async function handleCreate(e) {
        e.preventDefault();
        if (!nom.trim()) return;
        setBusy(true);
        setActionError('');
        try {
            const data = await createRouter(nom.trim());
            setConfig({ nom: data.router.nom, script: data.config_script });
            setNom('');
            setShowForm(false);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de la création du routeur.");
        } finally {
            setBusy(false);
        }
    }

    async function handleDelete(routerId) {
        if (!window.confirm('Supprimer ce routeur ? Cette action est définitive.')) return;
        setBusy(true);
        setActionError('');
        try {
            await deleteRouter(routerId);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de la suppression.");
        } finally {
            setBusy(false);
        }
    }

    async function handleRegenerate(routerId) {
        setBusy(true);
        setActionError('');
        try {
            const data = await regenerateRouter(routerId);
            setConfig({ nom: data.router.nom, script: data.config_script });
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de la régénération.");
        } finally {
            setBusy(false);
        }
    }

    async function handleActiverPack(routerId, packId) {
        setBusy(true);
        setActionError('');
        try {
            await activerPack(routerId, packId);
            setPackRouterId(null);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de l'activation du pack.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div>
            <div className="section-header">
                <h1 className="page-title">Mes routeurs</h1>
                <button className="btn-primary" onClick={() => navigate('/routers/nouveau')}>
                    <Plus size={16} /> Ajouter un routeur
                </button>
            </div>

            {actionError && <p className="error-text">{actionError}</p>}

            {showForm && (
                <form className="section-card" onSubmit={handleCreate}>
                    <label className="field-label" htmlFor="nom-routeur">Nom du routeur</label>
                    <div className="form-row">
                        <input
                            id="nom-routeur"
                            type="text"
                            value={nom}
                            onChange={(e) => setNom(e.target.value)}
                            placeholder="Ex : Routeur boutique"
                            className="text-input"
                        />
                        <button className="btn-primary" type="submit" disabled={busy}>Créer</button>
                    </div>
                </form>
            )}

            {loading && <p className="empty-hint">Chargement de vos routeurs...</p>}

            {!loading && routers.length === 0 && (
                <div className="section-card">
                    <p className="empty-hint">Vous n'avez encore aucun routeur.</p>
                    <button className="btn-primary" onClick={() => navigate('/routers/nouveau')}>
                        <Plus size={16} /> Commencer la configuration guidée
                    </button>
                </div>
            )}

            {!loading && normalizedQuery && filteredRouters.length === 0 && (
                <p className="search-empty-msg">Aucun résultat pour « {query} ».</p>
            )}

            <div className="routers-grid">
                {filteredRouters.map((r) => {
                    const statut = statutRouteur(r);
                    return (
                        <div key={r.id} className="section-card router-card">
                            <div className="section-header">
                                <h2>{r.nom}</h2>
                                <span className={`badge ${statut.cls}`}>{statut.label}</span>
                            </div>

                            <div className="router-meta">
                                <span>IP WireGuard : <strong>{r.wireguard_ip || '—'}</strong></span>
                                <span>Créé le {new Date(r.created_at).toLocaleDateString()}</span>
                                {r.subscription_expires_at && (
                                    <span>Abonnement jusqu'au {new Date(r.subscription_expires_at).toLocaleDateString()}</span>
                                )}
                                {!r.subscription_expires_at && r.trial_expires_at && (
                                    <span>Essai jusqu'au {new Date(r.trial_expires_at).toLocaleDateString()}</span>
                                )}
                            </div>

                            {r.ports?.length > 0 && (
                                <div className="ports-row">
                                    {r.ports.map((p) => (
                                        <span key={p.service_type} className="port-pill">
                                            {p.service_type} : {p.public_port}
                                        </span>
                                    ))}
                                </div>
                            )}

                            {packRouterId === r.id ? (
                                <div className="pack-picker">
                                    {packs.map((p) => (
                                        <button
                                            key={p.id}
                                            className="btn-secondary"
                                            disabled={busy}
                                            onClick={() => handleActiverPack(r.id, p.id)}
                                        >
                                            {p.label} — {p.montant} FCFA
                                        </button>
                                    ))}
                                    <button className="btn-secondary" onClick={() => setPackRouterId(null)}>
                                        <X size={14} /> Annuler
                                    </button>
                                </div>
                            ) : (
                                <div className="router-actions">
                                    <button className="btn-primary" onClick={() => setPackRouterId(r.id)}>
                                        <Zap size={14} /> Activer un pack
                                    </button>
                                    <button className="btn-secondary" disabled={busy} onClick={() => handleRegenerate(r.id)}>
                                        <RefreshCw size={14} /> Régénérer la config
                                    </button>
                                    <button className="btn-danger" disabled={busy} onClick={() => handleDelete(r.id)}>
                                        <Trash2 size={14} /> Supprimer
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {config && (
                <div className="modal-overlay" onClick={() => setConfig(null)}>
                    <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                        <div className="section-header">
                            <h2>Configuration — {config.nom}</h2>
                            <button className="btn-secondary" onClick={() => setConfig(null)}><X size={14} /></button>
                        </div>
                        <p className="empty-hint">Copiez ce script dans le terminal de votre routeur MikroTik.</p>
                        <pre className="config-script">{config.script}</pre>
                        <button className="btn-primary" onClick={() => navigator.clipboard.writeText(config.script)}>
                            <Copy size={14} /> Copier
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}