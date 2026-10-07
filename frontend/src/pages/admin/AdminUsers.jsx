import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import api from '../../api/client';
import Modal from '../hotspot/Modal';
import { useSearch } from '../../context/SearchContext';
import { stripAccents } from '../../utils/normalizeText';
import { confirmDialog } from '../../utils/confirm';
import { getErrorMessage } from '../../utils/errorMessage';
import '../Dashboard.css';
import './Admin.css';
import { formatAmount, formatDate, formatDateTime } from '../../utils/format';
import { KIND, SubscriptionModal, isActiveKind, routerDot, subscriptionLine } from './adminShared';

function signed(value) {
    return `${value >= 0 ? '+' : '−'} ${formatAmount(Math.abs(value))} F`;
}

function UserDetail({ userId, currentUserId, onClose, onChanged }) {
    const [user, setUser] = useState(null);
    const [error, setError] = useState('');
    const [info, setInfo] = useState('');
    const [busy, setBusy] = useState(false);
    const [editingRouter, setEditingRouter] = useState(null);
    const [sens, setSens] = useState('credit');
    const [montant, setMontant] = useState('');
    const [motif, setMotif] = useState('');

    const load = useCallback(() => api.get(`/admin/users/${userId}`)
        .then((res) => setUser(res.data))
        .catch((err) => setError(getErrorMessage(err, 'Impossible de charger ce revendeur.'))), [userId]);

    useEffect(() => {
        load();
    }, [load]);

    async function toggleRole() {
        const next = user.role === 'admin' ? 'client' : 'admin';
        const message = next === 'admin'
            ? `Nommer ${user.nom} administrateur ? Il aura accès à tout l'espace d'administration.`
            : `Retirer les droits d'administrateur de ${user.nom} ?`;
        if (!(await confirmDialog(message, { confirmLabel: 'Confirmer', danger: next === 'admin' }))) return;
        setBusy(true);
        setError('');
        try {
            await api.post(`/admin/users/${user.id}/role`, { role: next });
            setInfo(next === 'admin' ? `${user.nom} est maintenant administrateur.` : `${user.nom} n'est plus administrateur.`);
            await load();
            onChanged();
        } catch (err) {
            setError(getErrorMessage(err, 'Le rôle n\'a pas pu être modifié.'));
        } finally {
            setBusy(false);
        }
    }

    async function adjust(e) {
        e.preventDefault();
        const value = Number(montant);
        if (!Number.isInteger(value) || value <= 0) return setError('Indiquez un montant en FCFA (nombre entier).');
        if (motif.trim().length < 3) return setError('Indiquez le motif de la correction.');
        const signedValue = sens === 'credit' ? value : -value;
        if (!(await confirmDialog(
            `${sens === 'credit' ? 'Créditer' : 'Débiter'} ${formatAmount(value)} F ${sens === 'credit' ? 'sur' : 'du'} solde de ${user.nom} ? Motif : ${motif.trim()}`,
            { confirmLabel: 'Confirmer', danger: sens === 'debit' },
        ))) return;
        setBusy(true);
        setError('');
        try {
            await api.post(`/admin/users/${user.id}/ajustement`, { montant: signedValue, motif: motif.trim() });
            setInfo(`Solde corrigé de ${signed(signedValue)}.`);
            setMontant('');
            setMotif('');
            await load();
            onChanged();
        } catch (err) {
            setError(getErrorMessage(err, 'Le solde n\'a pas pu être corrigé.'));
        } finally {
            setBusy(false);
        }
    }

    return (
        <Modal title={user ? user.nom : 'Revendeur'} onClose={onClose} width={640}>
            {!user && !error && <p className="empty-hint">Chargement…</p>}
            {error && <p className="error-text">{error}</p>}
            {info && <p className="success-text">{info}</p>}
            {user && (
                <>
                    <p className="empty-hint ad-no-margin">
                        {user.email} · inscrit le {formatDate(user.created_at)} · essai {user.trial_used ? 'utilisé' : 'disponible'}
                    </p>
                    <div className="ad-detail-head">
                        <div><span className="ad-muted">Solde</span><b>{formatAmount(user.solde)} F</b></div>
                        <div>
                            <span className="ad-muted">Rôle</span>
                            <b>{user.role === 'admin' ? 'Administrateur' : 'Revendeur'}</b>
                        </div>
                        {user.id !== currentUserId && (
                            <button type="button" className="btn-secondary db-small" disabled={busy} onClick={toggleRole}>
                                {user.role === 'admin' ? 'Retirer les droits admin' : 'Nommer administrateur'}
                            </button>
                        )}
                    </div>

                    <h3 className="ad-h3">Routeurs ({user.routers.length})</h3>
                    {user.routers.length === 0 && <p className="empty-hint">Aucun routeur.</p>}
                    {user.routers.map((r) => {
                        const kind = KIND[r.abonnement] || KIND.aucun;
                        return (
                            <div key={r.id} className="ad-row">
                                <span className={`db-dot db-dot-${routerDot(r)}`} aria-hidden="true" />
                                <div className="ad-row-text">
                                    <div><strong>{r.nom}</strong> <span className={`badge ${kind.cls}`}>{kind.label}</span></div>
                                    <span>{subscriptionLine(r)} · {r.is_connected ? 'en ligne' : 'hors ligne'}</span>
                                </div>
                                <button type="button" className="btn-secondary db-small" onClick={() => setEditingRouter(r)}>
                                    {isActiveKind(r.abonnement) ? 'Abonnement' : 'Activer'}
                                </button>
                            </div>
                        );
                    })}

                    <h3 className="ad-h3">Corriger le solde</h3>
                    <form className="ad-adjust" onSubmit={adjust}>
                        <select className="text-input" value={sens} onChange={(e) => setSens(e.target.value)} aria-label="Sens">
                            <option value="credit">Créditer</option>
                            <option value="debit">Débiter</option>
                        </select>
                        <input className="text-input" type="number" min="1" step="1" placeholder="Montant (F)" value={montant} onChange={(e) => setMontant(e.target.value)} aria-label="Montant" />
                        <input className="text-input ad-grow" maxLength={200} placeholder="Motif (obligatoire)" value={motif} onChange={(e) => setMotif(e.target.value)} aria-label="Motif" />
                        <button type="submit" className="btn-secondary db-small" disabled={busy}>Valider</button>
                    </form>

                    <h3 className="ad-h3">Dernières opérations</h3>
                    {user.operations.length === 0 && <p className="empty-hint">Aucune opération.</p>}
                    {user.operations.map((t) => (
                        <div key={t.id} className="ad-row">
                            <div className="ad-row-text">
                                <div>{t.titre}</div>
                                <span>{formatDateTime(t.created_at)}{t.detail ? ` · ${t.detail}` : ''}</span>
                            </div>
                            <b className={t.montant_signe > 0 ? 'wl-in' : ''}>{signed(t.montant_signe)}</b>
                        </div>
                    ))}
                </>
            )}
            {editingRouter && (
                <SubscriptionModal
                    router={editingRouter}
                    onClose={() => setEditingRouter(null)}
                    onDone={(message) => { setEditingRouter(null); setInfo(message); load(); onChanged(); }}
                />
            )}
        </Modal>
    );
}

export default function AdminUsers() {
    const { user: me } = useOutletContext();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [openId, setOpenId] = useState(null);
    const { query } = useSearch();

    const load = useCallback(() => api.get('/admin/users')
        .then((res) => setUsers(res.data))
        .catch(() => setError('Impossible de charger les revendeurs.'))
        .finally(() => setLoading(false)), []);

    useEffect(() => {
        load();
    }, [load]);

    const q = stripAccents(query.trim());
    const visible = users.filter((u) => !q || stripAccents(`${u.nom} ${u.email}`).includes(q));

    return (
        <div className="db-page">
            <h1 className="page-title">Revendeurs</h1>
            {error && <p className="error-text">{error}</p>}
            {loading && <p className="empty-hint">Chargement…</p>}
            {!loading && visible.length === 0 && <p className="empty-hint">Aucun revendeur ne correspond.</p>}
            {visible.length > 0 && (
                <div className="section-card ad-list">
                    {visible.map((u) => (
                        <button key={u.id} type="button" className="ad-row ad-row-btn" onClick={() => setOpenId(u.id)}>
                            <div className="ad-row-text">
                                <div><strong>{u.nom}</strong> {u.role === 'admin' && <span className="badge badge-neutral">Admin</span>}</div>
                                <span>
                                    {u.email} · {u.nb_routers} routeur{u.nb_routers > 1 ? 's' : ''} · solde {formatAmount(u.solde)} F · inscrit le {formatDate(u.created_at)}
                                </span>
                            </div>
                            <span className="btn-secondary db-small">Détail</span>
                        </button>
                    ))}
                </div>
            )}
            {openId && (
                <UserDetail userId={openId} currentUserId={me?.id} onClose={() => setOpenId(null)} onChanged={load} />
            )}
        </div>
    );
}
