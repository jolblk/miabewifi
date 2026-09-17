import { useState, useEffect } from 'react';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import './Admin.css';

export default function AdminRouters() {
    const [routers, setRouters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { query } = useSearch();

    useEffect(() => {
        api.get('/admin/routers')
            .then((res) => setRouters(res.data))
            .catch(() => setError("Impossible de charger les routeurs."))
            .finally(() => setLoading(false));
    }, []);

    const normalizedQuery = stripAccents(query.trim());
    const filteredRouters = normalizedQuery
        ? routers.filter((r) => stripAccents(`${r.nom} ${r.proprietaire} ${r.proprietaire_email}`).includes(normalizedQuery))
        : routers;

    return (
        <div>
            <h1 className="page-title">Tous les routeurs</h1>
            <p className="greeting">{filteredRouters.length} routeur(s) au total.</p>

            {error && <p className="error-text">{error}</p>}
            {loading && <p className="empty-hint">Chargement...</p>}

            {!loading && normalizedQuery && filteredRouters.length === 0 && (
                <p className="search-empty-msg">Aucun résultat pour « {query} ».</p>
            )}

            {!loading && (
                <div className="section-card admin-table-wrap">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>Propriétaire</th>
                                <th>IP WireGuard</th>
                                <th>Connecté</th>
                                <th>Statut</th>
                                <th>Créé le</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredRouters.map((r) => (
                                <tr key={r.id}>
                                    <td>{r.nom}</td>
                                    <td>{r.proprietaire} <span style={{ color: 'var(--text-muted)' }}>({r.proprietaire_email})</span></td>
                                    <td>{r.wireguard_ip || '—'}</td>
                                    <td>{r.is_connected ? 'Oui' : 'Non'}</td>
                                    <td>
                                        <span className={`badge ${r.actif ? 'badge-success' : 'badge-danger'}`}>
                                            {r.actif ? 'Actif' : 'Inactif'}
                                        </span>
                                    </td>
                                    <td>{new Date(r.created_at).toLocaleDateString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}