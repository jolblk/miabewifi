import { useState, useEffect } from 'react';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import './Admin.css';

export default function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { query } = useSearch();

    useEffect(() => {
        api.get('/admin/users')
            .then((res) => setUsers(res.data))
            .catch(() => setError("Impossible de charger les utilisateurs."))
            .finally(() => setLoading(false));
    }, []);

    const normalizedQuery = stripAccents(query.trim());
    const filteredUsers = normalizedQuery
        ? users.filter((u) => stripAccents(`${u.nom} ${u.email}`).includes(normalizedQuery))
        : users;

    return (
        <div>
            <h1 className="page-title">Utilisateurs</h1>
            <p className="greeting">{filteredUsers.length} utilisateur(s) inscrit(s).</p>

            {error && <p className="error-text">{error}</p>}
            {loading && <p className="empty-hint">Chargement...</p>}

            {!loading && normalizedQuery && filteredUsers.length === 0 && (
                <p className="search-empty-msg">Aucun résultat pour « {query} ».</p>
            )}

            {!loading && (
                <div className="section-card admin-table-wrap">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>Email</th>
                                <th>Rôle</th>
                                <th>Solde</th>
                                <th>Routeurs</th>
                                <th>Inscrit le</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.map((u) => (
                                <tr key={u.id}>
                                    <td>{u.nom}</td>
                                    <td>{u.email}</td>
                                    <td>
                                        <span className={`badge ${u.role === 'admin' ? 'badge-success' : 'badge-warning'}`}>
                                            {u.role}
                                        </span>
                                    </td>
                                    <td>{u.solde} FCFA</td>
                                    <td>{u.nb_routers}</td>
                                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}