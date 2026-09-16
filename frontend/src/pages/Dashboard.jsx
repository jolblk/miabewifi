import { useOutletContext, useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import './Dashboard.css';

export default function Dashboard() {
    const { user } = useOutletContext();
    const navigate = useNavigate();
    const { solde, routers, actifs, prochaineEcheance, echeancesProches, aSurveiller, loading } = useDashboardData();

    return (
        <div>
            <h1 className="page-title">Mon compte</h1>
            <p className="greeting">Bonjour <strong>{user?.nom}</strong>, voici l'état de vos routeurs.</p>

            <button className="btn-secondary" onClick={() => navigate('/routers')}>
                Voir les abonnements
            </button>

            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-label">Solde portefeuille</div>
                    <div className="stat-number">{loading ? '--' : solde} <small>FCFA</small></div>
                    <div className="stat-sub">Rechargez pour activer des packs</div>
                    <div className="stat-actions">
                        <button className="btn-primary" onClick={() => navigate('/wallet')}>Recharger</button>
                        <button className="btn-secondary" onClick={() => navigate('/wallet')}>Retirer</button>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Mes routeurs</div>
                    <div className="stat-number">{actifs.length}<small>/{routers.length}</small></div>
                    <div className="stat-sub">
                        {routers.length === 0 ? 'Aucun routeur pour le moment' : `${actifs.length} routeur(s) actif(s) sur ${routers.length}`}
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Prochaine échéance</div>
                    <div className="stat-number" style={{ fontSize: 18 }}>
                        {prochaineEcheance ? prochaineEcheance.toLocaleDateString() : 'Aucune licence active'}
                    </div>
                    <div className="stat-sub">Activez un pack pour démarrer un routeur</div>
                </div>
            </div>

            <div className="section-card">
                <div className="section-header">
                    <h2>Statut de mes routeurs <span className="count-pill">{routers.length}</span></h2>
                    <button className="btn-secondary" onClick={() => navigate('/routers')}>Gérer</button>
                </div>
            </div>

            <div className="two-col">
                <div className="section-card">
                    <div className="section-header">
                        <h2>Échéances à venir <span className="count-pill">{echeancesProches.length}</span></h2>
                    </div>
                    {echeancesProches.length === 0 ? (
                        <p className="empty-hint"><CheckCircle2 size={16} /> Aucune licence n'expire dans les 7 prochains jours.</p>
                    ) : (
                        echeancesProches.map((r) => (
                            <div key={r.id} className="deadline-row">
                                <AlertTriangle size={16} />
                                <span><strong>{r.nom}</strong> expire le {new Date(r.subscription_expires_at).toLocaleDateString()}</span>
                            </div>
                        ))
                    )}
                </div>

                <div className="section-card">
                    <div className="section-header">
                        <h2>À activer / à surveiller <span className="count-pill">{aSurveiller.length}</span></h2>
                    </div>
                    {aSurveiller.length === 0 ? (
                        <p className="empty-hint"><CheckCircle2 size={16} /> Tous vos routeurs sont opérationnels.</p>
                    ) : (
                        aSurveiller.map((r) => (
                            <div key={r.id} className="watch-row">
                                <XCircle size={16} />
                                <span><strong>{r.nom}</strong> — accès expiré, pack à activer</span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}