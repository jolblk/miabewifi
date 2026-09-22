import { useOutletContext, useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, XCircle, Wallet } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import './Dashboard.css';

function routerStatus(r, now) {
    const trialActive = r.trial_expires_at && new Date(r.trial_expires_at) > now;
    const aboActive = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
    const expiryDate = r.subscription_expires_at ? new Date(r.subscription_expires_at) : null;
    const dans7j = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    if (!trialActive && !aboActive) {
        return { label: 'À activer', tone: 'danger', Icon: XCircle };
    }
    if (aboActive && expiryDate <= dans7j) {
        return { label: `Expire le ${expiryDate.toLocaleDateString()}`, tone: 'warning', Icon: AlertTriangle };
    }
    return { label: 'Actif', tone: 'success', Icon: CheckCircle2 };
}

export default function Dashboard() {
    const { user } = useOutletContext();
    const navigate = useNavigate();
    const { solde, routers, aSurveiller, loading } = useDashboardData();
    const now = new Date();

    return (
        <div>
            <h1 className="page-title">Bonjour {user?.nom}</h1>

            {!loading && aSurveiller.length > 0 && (
                <button className="alert-banner" onClick={() => navigate('/routers')}>
                    <XCircle size={20} />
                    <span>
                        {aSurveiller.length === 1
                            ? '1 routeur a besoin d\'un pack pour fonctionner'
                            : `${aSurveiller.length} routeurs ont besoin d'un pack pour fonctionner`}
                    </span>
                </button>
            )}

            <div className="wallet-card" onClick={() => navigate('/wallet')}>
                <div className="wallet-card-left">
                    <Wallet size={22} />
                    <div>
                        <div className="stat-label">Solde disponible</div>
                        <div className="stat-number">{loading ? '--' : solde} <small>FCFA</small></div>
                    </div>
                </div>
                <button className="btn-primary" onClick={(e) => { e.stopPropagation(); navigate('/wallet'); }}>
                    Gérer mon solde
                </button>
            </div>

            <div className="section-card">
                <div className="section-header">
                    <h2>Mes routeurs</h2>
                    {routers.length > 0 && (
                        <button className="btn-secondary" onClick={() => navigate('/routers')}>Voir tout</button>
                    )}
                </div>

                {routers.length === 0 ? (
                    <div className="empty-router-state">
                        <p className="empty-hint">Vous n'avez pas encore de routeur.</p>
                        <button className="btn-primary" onClick={() => navigate('/routers/nouveau')}>
                            Ajouter mon premier routeur
                        </button>
                    </div>
                ) : (
                    <div className="router-status-list">
                        {routers.map((r) => {
                            const { label, tone, Icon } = routerStatus(r, now);
                            return (
                                <button key={r.id} className="router-status-row" onClick={() => navigate('/routers')}>
                                    <span className={`status-dot status-${tone}`} />
                                    <span className="router-status-name">{r.nom}</span>
                                    <span className={`router-status-label tone-${tone}`}>
                                        <Icon size={14} /> {label}
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