import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../api/client';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import '../Dashboard.css';
import './Admin.css';
import { KIND, SubscriptionModal, isActiveKind, routerDot, subscriptionLine } from './adminShared';

const FILTERS = [
    { key: 'tous', label: 'Tous' },
    { key: 'sans_abonnement', label: 'Sans abonnement' },
    { key: 'hors_ligne', label: 'Hors ligne' },
    { key: 'offerts', label: 'Offerts' },
];

function matchesFilter(r, filtre) {
    if (filtre === 'sans_abonnement') return !isActiveKind(r.abonnement);
    if (filtre === 'hors_ligne') return !r.is_connected;
    if (filtre === 'offerts') return r.abonnement === 'offert';
    return true;
}

export default function AdminRouters() {
    const [searchParams] = useSearchParams();
    const [routers, setRouters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [info, setInfo] = useState('');
    const [filtre, setFiltre] = useState(searchParams.get('filtre') || 'tous');
    const [editing, setEditing] = useState(null);
    const { query } = useSearch();

    const load = useCallback(() => api.get('/admin/routers')
        .then((res) => setRouters(res.data))
        .catch(() => setError('Impossible de charger les routeurs.'))
        .finally(() => setLoading(false)), []);

    useEffect(() => {
        load();
    }, [load]);

    const q = stripAccents(query.trim());
    const visible = routers
        .filter((r) => matchesFilter(r, filtre))
        .filter((r) => !q || stripAccents(`${r.nom} ${r.proprietaire} ${r.proprietaire_email} ${r.wireguard_ip || ''}`).includes(q));

    return (
        <div className="db-page">
            <h1 className="page-title">Routeurs</h1>
            <div className="ad-chips">
                {FILTERS.map((f) => (
                    <button key={f.key} type="button" className={`wl-chip${filtre === f.key ? ' is-on' : ''}`} onClick={() => setFiltre(f.key)}>
                        {f.label} ({routers.filter((r) => matchesFilter(r, f.key)).length})
                    </button>
                ))}
            </div>
            {error && <p className="error-text">{error}</p>}
            {info && <p className="success-text">{info}</p>}
            {loading && <p className="empty-hint">Chargement…</p>}
            {!loading && visible.length === 0 && <p className="empty-hint">Aucun routeur ne correspond.</p>}

            {visible.length > 0 && (
                <div className="section-card ad-list">
                    {visible.map((r) => {
                        const kind = KIND[r.abonnement] || KIND.aucun;
                        const active = isActiveKind(r.abonnement);
                        return (
                            <div key={r.id} className="ad-row">
                                <span className={`db-dot db-dot-${routerDot(r)}`} aria-hidden="true" />
                                <div className="ad-row-text">
                                    <div><strong>{r.nom}</strong> <span className={`badge ${kind.cls}`}>{kind.label}</span></div>
                                    <span>
                                        {r.proprietaire} ({r.proprietaire_email}) · {subscriptionLine(r)} · {r.is_connected ? 'en ligne' : 'hors ligne'}
                                        {r.wireguard_ip ? ` · ${r.wireguard_ip}` : ''}
                                    </span>
                                </div>
                                <button type="button" className={active ? 'btn-secondary db-small' : 'btn-primary db-small'} onClick={() => { setInfo(''); setEditing(r); }}>
                                    {active ? 'Abonnement' : 'Activer'}
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}

            {editing && (
                <SubscriptionModal
                    router={editing}
                    onClose={() => setEditing(null)}
                    onDone={(message) => { setEditing(null); setInfo(message); load(); }}
                />
            )}
        </div>
    );
}
