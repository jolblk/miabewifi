import { useState } from 'react';
import { ArrowDownCircle, ArrowUpCircle } from 'lucide-react';
import { useWalletData } from '../hooks/useWalletData';
import './Wallet.css';

const statutLabel = { en_attente: 'En attente', confirme: 'Confirmé' };
const statutClass = { en_attente: 'badge-warning', confirme: 'badge-success' };
const typeLabel = { recharge: 'Recharge', debit: 'Pack activé', retrait: 'Retrait' };

export default function Wallet() {
    const { solde, transactions, loading, recharger, retirer } = useWalletData();

    const [mode, setMode] = useState('recharger');
    const [phone, setPhone] = useState('');
    const [network, setNetwork] = useState('FLOOZ');
    const [montant, setMontant] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!phone.trim() || !montant || Number(montant) <= 0) {
            setError('Renseigne un numéro et un montant valides.');
            return;
        }
        setBusy(true);
        try {
            if (mode === 'recharger') {
                const data = await recharger(phone.trim(), network, Number(montant));
                setSuccess(data.message || 'Demande envoyée. Valide sur ton téléphone.');
            } else {
                const data = await retirer(phone.trim(), network, Number(montant));
                setSuccess(data.message || 'Retrait effectué.');
            }
            setMontant('');
        } catch (err) {
            setError(err.response?.data?.detail || "Une erreur est survenue.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div>
            <h1 className="page-title">Portefeuille</h1>

            <div className="stat-card" style={{ marginBottom: 20, maxWidth: 320 }}>
                <div className="stat-label">Solde disponible</div>
                <div className="stat-number">{loading ? '--' : solde} <small>FCFA</small></div>
            </div>

            <div className="section-card">
                <div className="wallet-tabs">
                    <button
                        className={`wallet-tab ${mode === 'recharger' ? 'active' : ''}`}
                        onClick={() => { setMode('recharger'); setError(''); setSuccess(''); }}
                    >
                        <ArrowDownCircle size={16} /> Recharger
                    </button>
                    <button
                        className={`wallet-tab ${mode === 'retirer' ? 'active' : ''}`}
                        onClick={() => { setMode('retirer'); setError(''); setSuccess(''); }}
                    >
                        <ArrowUpCircle size={16} /> Retirer
                    </button>
                </div>

                {error && <p className="error-text">{error}</p>}
                {success && <p className="success-text">{success}</p>}

                <form className="form-stack" onSubmit={handleSubmit}>
                    <div>
                        <label className="field-label" htmlFor="phone">Numéro mobile money</label>
                        <input
                            id="phone"
                            type="tel"
                            className="text-input"
                            style={{ width: '100%' }}
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            placeholder="Ex : 90000000"
                        />
                    </div>

                    <div>
                        <label className="field-label" htmlFor="network">Opérateur</label>
                        <select
                            id="network"
                            className="select-input"
                            value={network}
                            onChange={(e) => setNetwork(e.target.value)}
                        >
                            <option value="FLOOZ">Flooz</option>
                            <option value="TMONEY">T-Money</option>
                        </select>
                    </div>

                    <div>
                        <label className="field-label" htmlFor="montant">Montant (FCFA)</label>
                        <input
                            id="montant"
                            type="number"
                            min="1"
                            className="text-input"
                            style={{ width: '100%' }}
                            value={montant}
                            onChange={(e) => setMontant(e.target.value)}
                            placeholder="Ex : 5000"
                        />
                    </div>

                    <button className="btn-primary" type="submit" disabled={busy}>
                        {mode === 'recharger' ? 'Recharger' : 'Retirer'}
                    </button>
                </form>
            </div>

            <div className="section-card">
                <div className="section-header">
                    <h2>Historique</h2>
                </div>
                {loading && <p className="empty-hint">Chargement...</p>}
                {!loading && transactions.length === 0 && (
                    <p className="empty-hint">Aucune transaction pour le moment.</p>
                )}
                <div className="tx-list">
                    {transactions.map((t) => {
                        const isCredit = t.type === 'recharge';
                        return (
                            <div key={t.id} className="tx-row">
                                <div className="tx-main">
                                    <span>{typeLabel[t.type] || t.type} — {t.methode}</span>
                                    <span className="tx-date">{new Date(t.created_at).toLocaleString()}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <span className={`tx-amount ${isCredit ? 'positive' : 'negative'}`}>
                                        {isCredit ? '+' : '-'}{t.montant} FCFA
                                    </span>
                                    <span className={`badge ${statutClass[t.statut] || 'badge-warning'}`}>
                                        {statutLabel[t.statut] || t.statut}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}