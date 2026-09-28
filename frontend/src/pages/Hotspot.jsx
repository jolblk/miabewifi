import { useState, useEffect } from 'react';
import { Plus, Ticket, Check, Download, RefreshCw } from 'lucide-react';
import { useHotspotData } from '../hooks/useHotspotData';
import './Hotspot.css';

// Un ticket peut cumuler plusieurs états : vendu, utilisé (le client s'est connecté), expiré.
function ticketBadges(v) {
    const sold = Boolean(v.sale);
    const used = Boolean(v.first_login_at);
    const expired = v.statut === 'EXPIRED';

    if (expired) {
        const badges = [{ label: 'Expiré', cls: 'badge-danger' }];
        if (sold) badges.unshift({ label: 'Vendu', cls: 'badge-warning' });
        return badges;
    }
    const badges = [];
    if (sold) badges.push({ label: 'Vendu', cls: 'badge-warning' });
    if (used) badges.push({ label: 'Utilisé', cls: 'badge-success' });
    if (badges.length === 0) badges.push({ label: 'Disponible', cls: 'badge-success' });
    return badges;
}

function batchSummary(batch) {
    let disponibles = 0;
    let vendus = 0;
    let expires = 0;
    batch.vouchers.forEach((v) => {
        if (v.statut === 'EXPIRED') expires += 1;
        else if (v.sale) vendus += 1;
        else disponibles += 1;
    });
    return `${disponibles} disponible(s) · ${vendus} vendu(s) · ${expires} expiré(s)`;
}

export default function Hotspot() {
    const {
        routers, selectedRouterId, setSelectedRouterId,
        batches, loading, error, profiles, currentRateLimit,
        generateBatch, sellVoucher, syncNow, applyRateLimit, installLoginPage, downloadBatchPdf,
    } = useHotspotData();

    const [showForm, setShowForm] = useState(false);
    const [profileName, setProfileName] = useState('');
    const [prixUnitaire, setPrixUnitaire] = useState('');
    const [quantite, setQuantite] = useState('');
    const [validiteJours, setValiditeJours] = useState('30');
    const [busy, setBusy] = useState(false);
    const [actionError, setActionError] = useState('');
    const [actionInfo, setActionInfo] = useState('');
    const [rateLimit, setRateLimit] = useState('');

    useEffect(() => {
        setRateLimit(currentRateLimit);
    }, [currentRateLimit]);

    async function handleGenerate(e) {
        e.preventDefault();
        if (!profileName.trim() || !prixUnitaire || !quantite) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            await generateBatch(profileName.trim(), Number(prixUnitaire), Number(quantite), validiteJours ? Number(validiteJours) : null);
            setProfileName('');
            setPrixUnitaire('');
            setQuantite('');
            setShowForm(false);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de la génération des tickets.");
        } finally {
            setBusy(false);
        }
    }

    async function handleSell(voucherId) {
        setBusy(true);
        setActionError('');
        try {
            await sellVoucher(voucherId);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Erreur lors de la vente du ticket.");
        } finally {
            setBusy(false);
        }
    }

    async function handleSync() {
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await syncNow();
            setActionInfo(`Mise à jour terminée : ${res.connexions_detectees} connexion(s) détectée(s), ${res.expires} ticket(s) expiré(s).`);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Impossible de mettre à jour les tickets.");
        } finally {
            setBusy(false);
        }
    }

    async function handleRateLimit(e) {
        e.preventDefault();
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await applyRateLimit(rateLimit.trim());
            setActionInfo(`Vitesse limitée à ${res.rate_limit} par client (${res.forfaits.join(', ')}).`);
        } catch (err) {
            const detail = err.response?.data?.detail;
            setActionError(typeof detail === 'string' ? detail : "Format invalide. Exemple : 2M/2M ou 512k/1M.");
        } finally {
            setBusy(false);
        }
    }

    async function handleInstallLoginPage() {
        if (!window.confirm("Installer la page de connexion simplifiée (un seul champ : le code) ? Elle remplace la page de connexion actuelle de votre HotSpot.")) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await installLoginPage();
            setActionInfo(res.message);
        } catch (err) {
            setActionError(err.response?.data?.detail || "Impossible d'installer la page de connexion.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div>
            <div className="section-header">
                <h1 className="page-title">Tickets HotSpot</h1>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn-secondary" onClick={handleSync} disabled={!selectedRouterId || busy}>
                        <RefreshCw size={16} /> Actualiser
                    </button>
                    <button className="btn-primary" onClick={() => setShowForm((v) => !v)} disabled={!selectedRouterId}>
                        <Plus size={16} /> Générer des tickets
                    </button>
                </div>
            </div>

            {routers.length > 0 && (
                <div className="hotspot-router-picker">
                    <label className="field-label" htmlFor="routeur-select">Routeur</label>
                    <select
                        id="routeur-select"
                        className="text-input"
                        value={selectedRouterId || ''}
                        onChange={(e) => setSelectedRouterId(Number(e.target.value))}
                    >
                        {routers.map((r) => (
                            <option key={r.id} value={r.id}>{r.nom}</option>
                        ))}
                    </select>
                </div>
            )}

            {!loading && routers.length === 0 && (
                <div className="section-card">
                    <p className="empty-hint">Ajoutez d'abord un routeur pour pouvoir générer des tickets HotSpot.</p>
                </div>
            )}

            {actionError && <p className="error-text">{actionError}</p>}
            {actionInfo && <p className="success-text">{actionInfo}</p>}
            {error && <p className="error-text">{error}</p>}

            {selectedRouterId && (
                <form className="section-card" onSubmit={handleRateLimit}>
                    <h2>Réglages du HotSpot</h2>
                    <label className="field-label" htmlFor="rate-limit">
                        Vitesse maximale par client (envoi/téléchargement)
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <input
                            id="rate-limit"
                            className="text-input"
                            style={{ maxWidth: 160 }}
                            value={rateLimit}
                            onChange={(e) => setRateLimit(e.target.value)}
                            placeholder="2M/2M"
                        />
                        <button className="btn-secondary" type="submit" disabled={busy || !rateLimit.trim()}>
                            Appliquer
                        </button>
                    </div>
                    <p className="empty-hint">
                        Évite qu'un seul client sature votre connexion. Exemples : 2M/2M, 1M/3M, 512k/1M.
                        S'applique à tous les forfaits « Ticket-… ».
                    </p>
                    <button type="button" className="btn-secondary" disabled={busy} onClick={handleInstallLoginPage}>
                        Installer la page de connexion simplifiée
                    </button>
                    <p className="empty-hint">
                        Le client saisit un seul champ (le code) au lieu de deux. Installée automatiquement sur les
                        routeurs configurés par MIABEWIFI.
                    </p>
                </form>
            )}

            {showForm && (
                <form className="section-card" onSubmit={handleGenerate}>
                    <label className="field-label" htmlFor="profile-name">Forfait</label>
                    <select
                        id="profile-name"
                        className="text-input"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                    >
                        <option value="">Choisir un forfait…</option>
                        {profiles.map((p) => (
                            <option key={p.name} value={p.name}>
                                {p.name}{p['session-timeout'] ? ` — ${p['session-timeout']} de connexion` : ''}
                            </option>
                        ))}
                    </select>
                    <label className="field-label" htmlFor="prix-unitaire">Prix unitaire (FCFA)</label>
                    <input
                        id="prix-unitaire"
                        type="number"
                        min="1"
                        value={prixUnitaire}
                        onChange={(e) => setPrixUnitaire(e.target.value)}
                        className="text-input"
                    />
                    <label className="field-label" htmlFor="quantite">Quantité</label>
                    <input
                        id="quantite"
                        type="number"
                        min="1"
                        max="500"
                        value={quantite}
                        onChange={(e) => setQuantite(e.target.value)}
                        className="text-input"
                    />
                    <label className="field-label" htmlFor="validite-jours">
                        Validité en jours après la 1re connexion (vide = sans limite)
                    </label>
                    <input
                        id="validite-jours"
                        type="number"
                        min="1"
                        max="365"
                        value={validiteJours}
                        onChange={(e) => setValiditeJours(e.target.value)}
                        className="text-input"
                    />
                    <p className="empty-hint">
                        La durée du forfait est du temps de connexion cumulé (ex : 24 h = 24 heures réellement connectées).
                        La validité est un délai calendaire : passé ce délai, le ticket est supprimé même s'il lui reste du temps.
                    </p>
                    <button className="btn-primary" type="submit" disabled={busy}>
                        {busy ? 'Génération en cours...' : 'Générer'}
                    </button>
                </form>
            )}

            {loading && <p className="empty-hint">Chargement des tickets...</p>}

            {!loading && batches.length === 0 && routers.length > 0 && (
                <div className="section-card">
                    <p className="empty-hint">Aucun ticket généré pour ce routeur pour le moment.</p>
                </div>
            )}

            <div className="hotspot-batches">
                {batches.map((batch) => (
                    <div key={batch.id} className="section-card">
                        <div className="section-header">
                            <div>
                                <h2>{batch.profile_name} — {batch.prix_unitaire} FCFA</h2>
                                <span className="empty-hint">
                                    {batchSummary(batch)}
                                    {batch.validite_jours ? ` · validité ${batch.validite_jours} j` : ''}
                                </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span className="empty-hint">{new Date(batch.created_at).toLocaleDateString()}</span>
                                <button className="btn-secondary" onClick={() => downloadBatchPdf(batch.id)}>
                                    <Download size={14} /> PDF
                                </button>
                            </div>
                        </div>
                        <div className="voucher-grid">
                            {batch.vouchers.map((v) => (
                                <div key={v.id} className="voucher-pill">
                                    <Ticket size={14} />
                                    <span>{v.code}</span>
                                    {ticketBadges(v).map((b) => (
                                        <span key={b.label} className={`badge ${b.cls}`}>{b.label}</span>
                                    ))}
                                    {v.statut === 'AVAILABLE' && (
                                        <button className="btn-secondary" disabled={busy} onClick={() => handleSell(v.id)}>
                                            <Check size={14} /> Vendre
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
