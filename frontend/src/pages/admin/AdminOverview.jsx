import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';
import api from '../../api/client';
import '../Dashboard.css';
import './Admin.css';
import { formatAmount, formatDateTime } from '../../utils/format';

function since(value) {
    const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
    if (minutes < 60) return `${minutes} min`;
    if (minutes < 48 * 60) return `${Math.round(minutes / 60)} h`;
    return `${Math.round(minutes / 1440)} jours`;
}

export default function AdminOverview() {
    const navigate = useNavigate();
    const [stats, setStats] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        api.get('/admin/stats')
            .then((res) => setStats(res.data))
            .catch(() => setError('Impossible de charger les statistiques.'));
    }, []);

    const tasks = [];
    if (stats) {
        if (stats.retraits_a_verifier > 0) {
            tasks.push({
                level: 'red',
                title: `${stats.retraits_a_verifier} retrait${stats.retraits_a_verifier > 1 ? 's' : ''} à vérifier dans PayGate`,
                hint: stats.plus_ancien_retrait ? `Le plus ancien attend depuis ${since(stats.plus_ancien_retrait)}` : '',
                action: 'Traiter', to: '/admin/transactions?statut=a_verifier',
            });
        }
        stats.remboursements_a_faire.forEach((p) => tasks.push({
            level: 'red',
            title: `Remboursement de ticket à faire à la main : ${formatAmount(p.montant)} F`,
            hint: `Vers ${p.reseau} ${p.telephone} · référence ${p.identifier}-remb · ${formatDateTime(p.created_at)}`,
        }));
        if (stats.abonnes_hors_ligne.length > 0) {
            tasks.push({
                level: 'orange',
                title: `${stats.abonnes_hors_ligne.length} routeur${stats.abonnes_hors_ligne.length > 1 ? 's' : ''} abonné${stats.abonnes_hors_ligne.length > 1 ? 's' : ''} hors ligne`,
                hint: stats.abonnes_hors_ligne.slice(0, 4).map((r) => r.nom).join(', ') + (stats.abonnes_hors_ligne.length > 4 ? '…' : ''),
                action: 'Voir', to: '/admin/routers?filtre=hors_ligne',
            });
        }
        if (stats.adresses_libres <= 40) {
            tasks.push({
                level: stats.adresses_libres <= 20 ? 'red' : 'orange',
                title: `Plus que ${stats.adresses_libres} adresses libres pour de nouveaux routeurs`,
                hint: 'Il faudra agrandir le réseau WireGuard du serveur.',
            });
        }
    }

    return (
        <div className="db-page">
            <h1 className="page-title">Vue d'ensemble</h1>
            {error && <p className="error-text">{error}</p>}
            {!stats && !error && <p className="empty-hint">Chargement…</p>}

            {stats && (
                <>
                    <div className="ad-kpis">
                        <div className="db-kpi"><span>Revendeurs</span><b>{formatAmount(stats.total_users)}</b></div>
                        <div className="db-kpi"><span>Routeurs actifs</span><b>{stats.routers_actifs} / {stats.total_routers}</b></div>
                        <div className="db-kpi"><span>En ligne maintenant</span><b>{stats.routers_en_ligne}</b></div>
                        <div className="db-kpi"><span>Ventes en ligne du mois</span><b>{formatAmount(stats.ventes_en_ligne_mois)} F</b></div>
                        <div className="db-kpi">
                            <span>Revenus MIABEWIFI du mois</span>
                            <b>{formatAmount(stats.revenus_mois)} F</b>
                            <small className="ad-muted">{formatAmount(stats.abonnements_mois)} F d'abonnements + {formatAmount(stats.frais_mois)} F de frais</small>
                        </div>
                    </div>

                    {tasks.length > 0 ? (
                        <div className="section-card db-tasks">
                            {tasks.map((t, i) => (
                                <div key={i} className="db-task">
                                    <span className={`db-dot db-dot-${t.level}`} aria-hidden="true" />
                                    <div className="db-task-text">
                                        <strong>{t.title}</strong>
                                        {t.hint && <span>{t.hint}</span>}
                                    </div>
                                    {t.to && <button type="button" className="btn-secondary db-small" onClick={() => navigate(t.to)}>{t.action}</button>}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="section-card db-ok"><CheckCircle2 size={18} /> Rien à traiter pour le moment.</div>
                    )}
                    <p className="empty-hint">Adresses libres pour de nouveaux routeurs : {stats.adresses_libres} sur 253.</p>
                </>
            )}
        </div>
    );
}
