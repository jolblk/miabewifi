import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import { confirmDialog } from '../../utils/confirm';
import { getErrorMessage } from '../../utils/errorMessage';
import '../Dashboard.css';
import './Admin.css';
import { formatAmount, formatDateTime } from '../../utils/format';

const TYPES = [
    { value: '', label: 'Tous les types' },
    { value: 'vente', label: 'Ventes en ligne' },
    { value: 'retrait', label: 'Retraits' },
    { value: 'recharge', label: 'Recharges' },
    { value: 'debit', label: 'Abonnements' },
    { value: 'ajustement', label: 'Corrections de solde' },
];
const STATUTS = [
    { value: '', label: 'Tous les statuts' },
    { value: 'a_verifier', label: 'À vérifier' },
    { value: 'en_attente', label: 'En attente' },
    { value: 'confirme', label: 'Confirmés' },
    { value: 'echoue', label: 'Échoués' },
];
const BADGES = {
    a_verifier: { label: 'À vérifier', cls: 'badge-warning' },
    en_attente: { label: 'En attente', cls: 'badge-warning' },
    echoue: { label: 'Échoué', cls: 'badge-danger' },
};

function signed(value) {
    return `${value >= 0 ? '+' : '−'} ${formatAmount(Math.abs(value))} F`;
}

export default function AdminTransactions() {
    const [searchParams] = useSearchParams();
    const [type, setType] = useState('');
    const [statut, setStatut] = useState(searchParams.get('statut') || '');
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [info, setInfo] = useState('');
    const [busyId, setBusyId] = useState(null);
    const { query } = useSearch();

    const load = useCallback(() => {
        setLoading(true);
        return api.get('/admin/transactions', { params: { type: type || undefined, statut: statut || undefined, limit: 300 } })
            .then((res) => setRows(res.data))
            .catch(() => setError('Impossible de charger les transactions.'))
            .finally(() => setLoading(false));
    }, [type, statut]);

    useEffect(() => {
        load();
    }, [load]);

    async function resolveWithdrawal(t, action) {
        const message = action === 'confirmer'
            ? `Confirmer que ${formatAmount(t.montant)} F sont bien arrivés chez ${t.user_nom} (référence ${t.identifier}) ? Vérifiez d'abord dans le tableau de bord PayGate.`
            : `Rendre ${formatAmount(t.montant)} F au solde de ${t.user_nom} (référence ${t.identifier}) ? Seulement si PayGate confirme que l'argent n'est pas parti.`;
        if (!(await confirmDialog(message, { confirmLabel: action === 'confirmer' ? 'Argent arrivé' : 'Rembourser', danger: action === 'rembourser' }))) return;
        setBusyId(t.id);
        setError('');
        setInfo('');
        try {
            const res = await api.post(`/admin/retraits/${t.id}/${action}`);
            setInfo(res.data.message);
            await load();
        } catch (err) {
            setError(getErrorMessage(err, "L'action n'a pas pu être effectuée."));
        } finally {
            setBusyId(null);
        }
    }

    const q = stripAccents(query.trim());
    const visible = rows.filter((t) => !q || stripAccents(`${t.user_nom} ${t.identifier} ${t.titre} ${t.detail || ''} ${t.note || ''}`).includes(q));

    return (
        <div className="db-page">
            <h1 className="page-title">Transactions</h1>
            <div className="ad-filters">
                <select className="text-input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
                    {TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <select className="text-input" value={statut} onChange={(e) => setStatut(e.target.value)} aria-label="Statut">
                    {STATUTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
            </div>
            {statut === 'a_verifier' && (
                <p className="empty-hint ad-no-margin">
                    PayGate n'a pas donné de réponse claire pour ces retraits. Cherchez la référence dans le tableau de bord PayGate :
                    si l'argent est arrivé, cliquez sur « Argent arrivé », sinon sur « Rembourser ».
                </p>
            )}
            {error && <p className="error-text">{error}</p>}
            {info && <p className="success-text">{info}</p>}
            {loading && <p className="empty-hint">Chargement…</p>}
            {!loading && visible.length === 0 && <p className="empty-hint">Aucune transaction ne correspond.</p>}

            {visible.length > 0 && (
                <div className="section-card ad-list">
                    {visible.map((t) => {
                        const badge = BADGES[t.statut];
                        return (
                            <div key={t.id} className="ad-row">
                                <div className="ad-row-text">
                                    <div>{t.titre} {badge && <span className={`badge ${badge.cls}`}>{badge.label}</span>}</div>
                                    <span>
                                        {t.user_nom} · {formatDateTime(t.created_at)}{t.detail ? ` · ${t.detail}` : ''}
                                    </span>
                                    <span className="mono ad-ref">{t.identifier}</span>
                                </div>
                                <b className={t.montant_signe > 0 ? 'wl-in' : ''}>{signed(t.montant_signe)}</b>
                                {t.type === 'retrait' && t.statut === 'a_verifier' && (
                                    <div className="ad-actions">
                                        <button type="button" className="btn-primary db-small" disabled={busyId === t.id} onClick={() => resolveWithdrawal(t, 'confirmer')}>Argent arrivé</button>
                                        <button type="button" className="btn-secondary db-small" disabled={busyId === t.id} onClick={() => resolveWithdrawal(t, 'rembourser')}>Rembourser</button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
