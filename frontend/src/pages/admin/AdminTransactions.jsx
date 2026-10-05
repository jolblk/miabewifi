import { useState, useEffect, useCallback } from 'react';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import { confirmDialog } from '../../utils/confirm';
import { getErrorMessage } from '../../utils/errorMessage';
import './Admin.css';
import { formatAmount, formatDateTime } from '../../utils/format';

const statutClass = { en_attente: 'badge-warning', confirme: 'badge-success', a_verifier: 'badge-warning', echoue: 'badge-danger' };
const statutLabel = { en_attente: 'En attente', confirme: 'Confirmé', a_verifier: 'À vérifier', echoue: 'Échoué' };
const typeLabel = { recharge: 'Recharge', vente: 'Vente de ticket', debit: 'Pack activé', retrait: 'Retrait' };

export default function AdminTransactions() {
    const [transactions, setTransactions] = useState([]);
    const [toCheck, setToCheck] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [actionMsg, setActionMsg] = useState('');
    const [busyId, setBusyId] = useState(null);
    const { query } = useSearch();

    const load = useCallback(() => {
        return Promise.all([
            api.get('/admin/transactions'),
            api.get('/admin/retraits-a-verifier'),
        ])
            .then(([txRes, checkRes]) => {
                setTransactions(txRes.data);
                setToCheck(checkRes.data);
            })
            .catch(() => setError("Impossible de charger les transactions."))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    async function resolveWithdrawal(w, action) {
        const message = action === 'confirmer'
            ? `Confirmer que ${formatAmount(w.montant)} FCFA sont bien arrivés chez ${w.user_nom} (référence ${w.identifier}) ? Vérifiez d'abord dans le tableau de bord PayGate.`
            : `Rendre ${formatAmount(w.montant)} FCFA au solde de ${w.user_nom} (référence ${w.identifier}) ? À faire UNIQUEMENT si PayGate confirme que l'argent n'est pas parti.`;
        const ok = await confirmDialog(message, {
            confirmLabel: action === 'confirmer' ? 'Confirmer le retrait' : 'Rembourser',
            danger: action === 'rembourser',
        });
        if (!ok) return;

        setBusyId(w.id);
        setError('');
        setActionMsg('');
        try {
            const res = await api.post(`/admin/retraits/${w.id}/${action}`);
            setActionMsg(res.data.message);
            await load();
        } catch (err) {
            setError(getErrorMessage(err, "L'action n'a pas pu être effectuée."));
        } finally {
            setBusyId(null);
        }
    }

    const normalizedQuery = stripAccents(query.trim());
    const filteredTransactions = normalizedQuery
        ? transactions.filter((t) => stripAccents(`${t.user_nom} ${t.methode} ${t.type} ${t.identifier || ''}`).includes(normalizedQuery))
        : transactions;

    return (
        <div>
            <h1 className="page-title">Transactions</h1>

            {error && <p className="error-text">{error}</p>}
            {actionMsg && <p className="greeting">{actionMsg}</p>}
            {loading && <p className="empty-hint">Chargement...</p>}

            {!loading && toCheck.length > 0 && (
                <div className="section-card admin-table-wrap">
                    <h2>Retraits à vérifier ({toCheck.length})</h2>
                    <p className="greeting">
                        PayGate n'a pas donné de réponse claire pour ces retraits. Cherchez la référence dans le
                        tableau de bord PayGate : si l'argent est arrivé, confirmez ; sinon, remboursez.
                    </p>
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Utilisateur</th>
                                <th>Référence</th>
                                <th>Méthode</th>
                                <th>Montant</th>
                                <th>Date</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {toCheck.map((w) => (
                                <tr key={w.id}>
                                    <td>{w.user_nom}<br /><small>{w.user_email}</small></td>
                                    <td><code>{w.identifier}</code></td>
                                    <td>{w.methode}</td>
                                    <td>{formatAmount(w.montant)} FCFA</td>
                                    <td>{formatDateTime(w.created_at)}</td>
                                    <td>
                                        <button
                                            className="btn-primary"
                                            disabled={busyId === w.id}
                                            onClick={() => resolveWithdrawal(w, 'confirmer')}
                                        >
                                            Argent arrivé
                                        </button>{' '}
                                        <button
                                            className="btn-secondary"
                                            disabled={busyId === w.id}
                                            onClick={() => resolveWithdrawal(w, 'rembourser')}
                                        >
                                            Rembourser
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <p className="greeting">100 dernières transactions.</p>

            {!loading && normalizedQuery && filteredTransactions.length === 0 && (
                <p className="search-empty-msg">Aucun résultat pour « {query} ».</p>
            )}

            {!loading && (
                <div className="section-card admin-table-wrap">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Utilisateur</th>
                                <th>Type</th>
                                <th>Méthode</th>
                                <th>Montant</th>
                                <th>Statut</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredTransactions.map((t) => (
                                <tr key={t.id}>
                                    <td>{t.user_nom}</td>
                                    <td>{typeLabel[t.type] || t.type}</td>
                                    <td>{t.methode}</td>
                                    <td>{formatAmount(t.montant)} FCFA</td>
                                    <td>
                                        <span className={`badge ${statutClass[t.statut] || 'badge-warning'}`}>
                                            {statutLabel[t.statut] || t.statut}
                                        </span>
                                    </td>
                                    <td>{formatDateTime(t.created_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
