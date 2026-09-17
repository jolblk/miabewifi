import { useState, useEffect } from 'react';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import './Admin.css';

const statutClass = { en_attente: 'badge-warning', confirme: 'badge-success' };
const typeLabel = { recharge: 'Recharge', debit: 'Pack activé', retrait: 'Retrait' };

export default function AdminTransactions() {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { query } = useSearch();

    useEffect(() => {
        api.get('/admin/transactions')
            .then((res) => setTransactions(res.data))
            .catch(() => setError("Impossible de charger les transactions."))
            .finally(() => setLoading(false));
    }, []);

    const normalizedQuery = stripAccents(query.trim());
    const filteredTransactions = normalizedQuery
        ? transactions.filter((t) => stripAccents(`${t.user_nom} ${t.methode} ${t.type}`).includes(normalizedQuery))
        : transactions;

    return (
        <div>
            <h1 className="page-title">Transactions</h1>
            <p className="greeting">100 dernières transactions.</p>

            {error && <p className="error-text">{error}</p>}
            {loading && <p className="empty-hint">Chargement...</p>}

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
                                    <td>{t.montant} FCFA</td>
                                    <td>
                                        <span className={`badge ${statutClass[t.statut] || 'badge-warning'}`}>
                                            {t.statut}
                                        </span>
                                    </td>
                                    <td>{new Date(t.created_at).toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}