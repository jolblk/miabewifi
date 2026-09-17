import { useState, useEffect } from 'react';
import api from '../../api/client';
import '../Dashboard.css';
import './Admin.css';

export default function AdminOverview() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        api.get('/admin/stats')
            .then((res) => setStats(res.data))
            .catch(() => setError("Impossible de charger les statistiques."))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div>
            <h1 className="page-title">Vue d'ensemble</h1>
            <p className="greeting">Statistiques globales de la plateforme.</p>

            {error && <p className="error-text">{error}</p>}
            {loading && <p className="empty-hint">Chargement...</p>}

            {stats && (
                <div className="admin-stats-grid">
                    <div className="stat-card">
                        <div className="stat-label">Utilisateurs</div>
                        <div className="stat-number">{stats.total_users}</div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-label">Routeurs</div>
                        <div className="stat-number">{stats.total_routers}</div>
                        <div className="stat-sub">{stats.routers_actifs} actifs / {stats.routers_inactifs} inactifs</div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-label">Revenus (30 derniers jours)</div>
                        <div className="stat-number">{stats.revenus_30j} <small>FCFA</small></div>
                        <div className="stat-sub">Total cumulé : {stats.revenus_total} FCFA</div>
                    </div>
                </div>
            )}
        </div>
    );
}