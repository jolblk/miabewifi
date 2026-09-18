import { useState } from 'react';
import { Plus, Ticket, Check, Download } from 'lucide-react';
import { useHotspotData } from '../hooks/useHotspotData';
import './Hotspot.css';

function statutBadge(statut) {
    if (statut === 'AVAILABLE') return { label: 'Disponible', cls: 'badge-success' };
    if (statut === 'USED') return { label: 'Vendu', cls: 'badge-warning' };
    return { label: 'Expiré', cls: 'badge-danger' };
}

export default function Hotspot() {
    const {
        routers, selectedRouterId, setSelectedRouterId,
        batches, loading, error,
        generateBatch, sellVoucher, downloadBatchPdf,
    } = useHotspotData();

    const [showForm, setShowForm] = useState(false);
    const [profileName, setProfileName] = useState('');
    const [prixUnitaire, setPrixUnitaire] = useState('');
    const [quantite, setQuantite] = useState('');
    const [busy, setBusy] = useState(false);
    const [actionError, setActionError] = useState('');

    async function handleGenerate(e) {
        e.preventDefault();
        if (!profileName.trim() || !prixUnitaire || !quantite) return;
        setBusy(true);
        setActionError('');
        try {
            await generateBatch(profileName.trim(), Number(prixUnitaire), Number(quantite));
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

    return (
        <div>
            <div className="section-header">
                <h1 className="page-title">Tickets HotSpot</h1>
                <button className="btn-primary" onClick={() => setShowForm((v) => !v)} disabled={!selectedRouterId}>
                    <Plus size={16} /> Générer des tickets
                </button>
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
            {error && <p className="error-text">{error}</p>}

            {showForm && (
                <form className="section-card" onSubmit={handleGenerate}>
                    <label className="field-label" htmlFor="profile-name">Profil HotSpot (nom exact sur le MikroTik)</label>
                    <input
                        id="profile-name"
                        type="text"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        placeholder="Ex : 1H"
                        className="text-input"
                    />
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
                            <h2>{batch.profile_name} — {batch.prix_unitaire} FCFA</h2>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span className="empty-hint">{new Date(batch.created_at).toLocaleDateString()}</span>
                                <button className="btn-secondary" onClick={() => downloadBatchPdf(batch.id)}>
                                    <Download size={14} /> PDF
                                </button>
                            </div>
                        </div>
                        <div className="voucher-grid">
                            {batch.vouchers.map((v) => {
                                const statut = statutBadge(v.statut);
                                return (
                                    <div key={v.id} className="voucher-pill">
                                        <Ticket size={14} />
                                        <span>{v.code}</span>
                                        <span className={`badge ${statut.cls}`}>{statut.label}</span>
                                        {v.statut === 'AVAILABLE' && (
                                            <button className="btn-secondary" disabled={busy} onClick={() => handleSell(v.id)}>
                                                <Check size={14} /> Vendre
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}