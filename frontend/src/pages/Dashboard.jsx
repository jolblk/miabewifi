import { useOutletContext, useNavigate } from 'react-router-dom';
import { ArrowUpRight, CheckCircle2, Plus, Ticket } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import { routerHealth } from './hotspot/hotspotUtils';
import './Dashboard.css';
import { formatAmount, formatDate } from '../utils/format';

const DAY = 24 * 60 * 60 * 1000;

function daysUntil(date, now) {
    return Math.max(0, Math.ceil((date - now) / DAY));
}

function inDays(n) {
    if (n === 0) return "aujourd'hui";
    if (n === 1) return 'demain';
    return `dans ${n} jours`;
}

// Liste « à faire », de la plus grave à la moins grave, chaque ligne menant à la solution.
function buildTasks({ routers, statuses, resume, reserve, now }) {
    const tasks = [];
    routers.forEach((r) => {
        const h = routerHealth(r, statuses[r.id]);
        const offline = h.online === false;
        if (!h.subscription.active) {
            tasks.push({
                level: 'red',
                title: offline ? `${r.nom} est hors ligne et sans abonnement` : `${r.nom} n'a plus d'abonnement`,
                hint: 'Vos clients ne peuvent plus acheter de tickets en ligne, et vous ne pouvez plus en créer.',
                action: 'Activer un forfait',
                to: '/routers',
            });
        } else if (offline) {
            tasks.push({
                level: 'red',
                title: `${r.nom} est hors ligne`,
                hint: "Vérifiez qu'il est allumé et relié à Internet.",
                action: 'Voir le routeur',
                to: '/routers',
            });
        } else if (h.subscription.date && h.subscription.date - now <= 7 * DAY) {
            const n = daysUntil(h.subscription.date, now);
            tasks.push({
                level: 'orange',
                title: h.subscription.kind === 'essai'
                    ? `L'essai gratuit de ${r.nom} se termine ${inDays(n)}`
                    : `L'abonnement de ${r.nom} expire ${inDays(n)}`,
                hint: `Le ${formatDate(h.subscription.date)}`,
                action: h.subscription.kind === 'essai' ? 'Activer un forfait' : 'Renouveler',
                to: '/routers',
            });
        }
    });
    (resume?.stock || []).forEach((s) => {
        const r = routers.find((x) => x.id === s.router_id);
        if (!r) return;
        tasks.push({
            level: s.niveau === 'epuise' ? 'red' : 'orange',
            title: s.niveau === 'epuise'
                ? `Plus aucun ticket « ${s.forfait} » sur ${r.nom}`
                : `Plus que ${s.disponibles} ticket${s.disponibles > 1 ? 's' : ''} « ${s.forfait} » sur ${r.nom}`,
            hint: `${formatAmount(s.prix)} F le ticket`,
            action: 'Créer des tickets',
            to: `/tickets?action=creer&routeur=${r.id}&forfait=${encodeURIComponent(s.profile_name)}`,
        });
    });
    if (reserve > 0) {
        tasks.push({
            level: 'orange',
            title: `Retrait de ${formatAmount(reserve)} F en vérification`,
            hint: "L'opérateur n'a pas encore confirmé. Le montant reste réservé : ne refaites pas la demande.",
            action: 'Voir le portefeuille',
            to: '/wallet',
        });
    }
    return tasks.sort((a, b) => (a.level === 'red' ? 0 : 1) - (b.level === 'red' ? 0 : 1));
}

function routerSubtitle(r, health, now) {
    const sub = health.subscription;
    const parts = [];
    if (health.online === false) parts.push('Hors ligne');
    if (sub.kind === 'abonnement') {
        parts.push(sub.date - now <= 7 * DAY ? `Expire ${inDays(daysUntil(sub.date, now))}` : `Abonné jusqu'au ${formatDate(sub.date)}`);
    } else if (sub.kind === 'essai') {
        parts.push(`Essai jusqu'au ${formatDate(sub.date)}`);
    } else if (sub.kind === 'expire') {
        parts.push('Abonnement expiré');
    } else {
        parts.push('À activer');
    }
    return parts.join(' · ');
}

export default function Dashboard() {
    const { user } = useOutletContext();
    const navigate = useNavigate();
    const { solde, reserve, routers, statuses, clients, resume, loading } = useDashboardData();
    const now = new Date();

    const tasks = loading ? [] : buildTasks({ routers, statuses, resume, reserve, now });
    const clientValues = routers.map((r) => clients[r.id]).filter((v) => typeof v === 'number');
    const totalClients = clientValues.length ? clientValues.reduce((a, b) => a + b, 0) : null;
    const trend = resume && resume.hier > 0 ? Math.round(((resume.aujourdhui - resume.hier) / resume.hier) * 100) : null;
    const today = now.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

    return (
        <div className="db-page">
            <div className="db-head">
                <div>
                    <h1 className="page-title db-title">Bonjour {user?.nom}</h1>
                    <span className="empty-hint db-sub">
                        {today.charAt(0).toUpperCase() + today.slice(1)}
                        {routers.length > 0 ? ` · ${routers.length} routeur${routers.length > 1 ? 's' : ''}` : ''}
                    </span>
                </div>
                {routers.length > 0 && (
                    <div className="db-actions">
                        <button type="button" className="btn-primary" onClick={() => navigate('/tickets?action=vendre')}>
                            <Ticket size={16} /> Vendre un ticket
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => navigate('/tickets?action=creer')}>
                            <Plus size={16} /> Créer des tickets
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => navigate('/wallet?action=retirer')}>
                            <ArrowUpRight size={16} /> Retirer
                        </button>
                    </div>
                )}
            </div>

            {!loading && routers.length > 0 && (
                tasks.length > 0 ? (
                    <div className="section-card db-tasks">
                        {tasks.map((t, i) => (
                            <div key={i} className="db-task">
                                <span className={`db-dot db-dot-${t.level}`} aria-hidden="true" />
                                <div className="db-task-text">
                                    <strong>{t.title}</strong>
                                    <span>{t.hint}</span>
                                </div>
                                <button type="button" className="btn-secondary db-small" onClick={() => navigate(t.to)}>{t.action}</button>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="section-card db-ok">
                        <CheckCircle2 size={18} /> Tout est en ordre : routeurs en ligne, abonnements à jour, stock suffisant.
                    </div>
                )
            )}

            <div className="db-kpis">
                <button type="button" className="db-kpi" onClick={() => navigate('/tickets')}>
                    <span>Recettes aujourd'hui</span>
                    <b>{resume ? `${formatAmount(resume.aujourdhui)} F` : '--'}</b>
                    {trend !== null && (
                        <small className={trend >= 0 ? 'db-up' : 'db-down'}>
                            {trend >= 0 ? '+' : '−'} {Math.abs(trend)} % par rapport à hier
                        </small>
                    )}
                </button>
                <button type="button" className="db-kpi" onClick={() => navigate('/tickets')}>
                    <span>Tickets vendus aujourd'hui</span>
                    <b>{resume ? formatAmount(resume.tickets_aujourdhui) : '--'}</b>
                </button>
                <button type="button" className="db-kpi" onClick={() => navigate('/tickets?vue=direct')}>
                    <span>Clients connectés</span>
                    <b>{totalClients === null ? '—' : totalClients}</b>
                </button>
                <button type="button" className="db-kpi" onClick={() => navigate('/wallet')}>
                    <span>Solde disponible</span>
                    <b>{solde === null ? '--' : `${formatAmount(solde)} F`}</b>
                </button>
            </div>

            <div className="section-card">
                <div className="section-header">
                    <h2>Mes routeurs</h2>
                    {routers.length > 0 && (
                        <button className="btn-secondary db-small" onClick={() => navigate('/routers')}>Voir tout</button>
                    )}
                </div>
                {!loading && routers.length === 0 ? (
                    <div className="empty-router-state">
                        <p className="empty-hint">Ajoutez votre premier routeur pour commencer à vendre des tickets Wi-Fi.</p>
                        <button className="btn-primary" onClick={() => navigate('/routers/nouveau')}>
                            Ajouter mon premier routeur
                        </button>
                    </div>
                ) : (
                    <div className="db-routers">
                        {routers.map((r) => {
                            const health = routerHealth(r, statuses[r.id]);
                            const day = resume?.par_routeur?.[String(r.id)];
                            const n = clients[r.id];
                            return (
                                <button key={r.id} type="button" className="db-router" onClick={() => navigate(`/tickets?routeur=${r.id}`)}>
                                    <span className={`db-dot db-dot-${health.color}`} aria-hidden="true" />
                                    <span className="db-router-name">
                                        <strong>{r.nom}</strong>
                                        <span>{routerSubtitle(r, health, now)}</span>
                                    </span>
                                    <span className="db-router-clients">
                                        {typeof n === 'number' ? `${n} connecté${n > 1 ? 's' : ''}` : '—'}
                                    </span>
                                    <span className="db-router-sales">
                                        <strong>{formatAmount(day?.aujourdhui || 0)} F</strong>
                                        <span>aujourd'hui</span>
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
