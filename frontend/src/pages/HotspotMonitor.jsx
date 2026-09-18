import { useState } from 'react';
import { RefreshCw, Users, Activity, Layers } from 'lucide-react';
import { useHotspotMonitor } from '../hooks/useHotspotMonitor';
import './HotspotMonitor.css';

const TABS = [
    { key: 'sessions', label: 'Sessions actives', icon: Activity },
    { key: 'users', label: 'Utilisateurs', icon: Users },
    { key: 'profiles', label: 'Profils', icon: Layers },
];

export default function HotspotMonitor() {
    const {
        routers, selectedRouterId, setSelectedRouterId,
        users, profiles, sessions,
        loading, error, refresh,
    } = useHotspotMonitor();

    const [activeTab, setActiveTab] = useState('sessions');

    return (
        <div>
            <div className="section-header">
                <h1 className="page-title">Suivi HotSpot</h1>
                <button className="btn-secondary" onClick={refresh} disabled={loading}>
                    <RefreshCw size={16} /> Actualiser
                </button>
            </div>

            {routers.length > 0 && (
                <div className="hotspot-router-picker">
                    <label className="field-label" htmlFor="monitor-routeur-select">Routeur</label>
                    <select
                        id="monitor-routeur-select"
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
                    <p className="empty-hint">Ajoutez d'abord un routeur pour voir son activité HotSpot.</p>
                </div>
            )}

            {error && <p className="error-text">{error}</p>}

            <div className="hotspot-tabs">
                {TABS.map((tab) => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.key}
                            className={`hotspot-tab ${activeTab === tab.key ? 'hotspot-tab-active' : ''}`}
                            onClick={() => setActiveTab(tab.key)}
                        >
                            <Icon size={16} /> {tab.label}
                        </button>
                    );
                })}
            </div>

            {loading && <p className="empty-hint">Chargement...</p>}

            {!loading && activeTab === 'sessions' && (
                <div className="section-card">
                    {sessions.length === 0 ? (
                        <p className="empty-hint">Aucun client connecté en ce moment.</p>
                    ) : (
                        <table className="hotspot-table">
                            <thead>
                                <tr>
                                    <th>Utilisateur</th>
                                    <th>Adresse IP</th>
                                    <th>Adresse MAC</th>
                                    <th>Connecté depuis</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sessions.map((s, i) => (
                                    <tr key={s['.id'] || i}>
                                        <td>{s.user}</td>
                                        <td>{s.address}</td>
                                        <td>{s['mac-address']}</td>
                                        <td>{s.uptime}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {!loading && activeTab === 'users' && (
                <div className="section-card">
                    {users.length === 0 ? (
                        <p className="empty-hint">Aucun utilisateur HotSpot sur ce routeur.</p>
                    ) : (
                        <table className="hotspot-table">
                            <thead>
                                <tr>
                                    <th>Nom</th>
                                    <th>Profil</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u, i) => (
                                    <tr key={u['.id'] || i}>
                                        <td>{u.name}</td>
                                        <td>{u.profile}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {!loading && activeTab === 'profiles' && (
                <div className="section-card">
                    {profiles.length === 0 ? (
                        <p className="empty-hint">Aucun profil HotSpot configuré sur ce routeur.</p>
                    ) : (
                        <table className="hotspot-table">
                            <thead>
                                <tr>
                                    <th>Nom</th>
                                    <th>Limite de débit</th>
                                    <th>Utilisateurs partagés</th>
                                </tr>
                            </thead>
                            <tbody>
                                {profiles.map((p, i) => (
                                    <tr key={p['.id'] || i}>
                                        <td>{p.name}</td>
                                        <td>{p['rate-limit'] || '—'}</td>
                                        <td>{p['shared-users'] || '1'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    );
}