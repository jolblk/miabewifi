import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';
import api from '../../api/client';
import '../Dashboard.css';
import './Admin.css';
import { formatAmount, formatDateTime } from '../../utils/format';
import { getErrorMessage } from '../../utils/errorMessage';

function since(value) {
    const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
    if (minutes < 60) return `${minutes} min`;
    if (minutes < 48 * 60) return `${Math.round(minutes / 60)} h`;
    return `${Math.round(minutes / 1440)} jours`;
}

// Pourcentage prélevé sur chaque retrait du portefeuille (couvre les frais PayGate).
function WithdrawalFeeCard() {
    const [value, setValue] = useState('');
    const [saved, setSaved] = useState(null);
    const [max, setMax] = useState(20);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        api.get('/admin/parametres')
            .then((res) => {
                setSaved(res.data.frais_retrait_pourcent);
                setValue(String(res.data.frais_retrait_pourcent));
                setMax(res.data.frais_retrait_max);
            })
            .catch(() => setError('Impossible de charger les frais de retrait.'));
    }, []);

    async function save(e) {
        e.preventDefault();
        const percent = Number(String(value).replace(',', '.'));
        if (!Number.isFinite(percent) || percent < 0 || percent > max) {
            setError(`Indiquez un pourcentage entre 0 et ${max}.`);
            return;
        }
        setBusy(true);
        setError('');
        setMessage('');
        try {
            const res = await api.put('/admin/parametres', { frais_retrait_pourcent: percent });
            setSaved(res.data.frais_retrait_pourcent);
            setValue(String(res.data.frais_retrait_pourcent));
            setMessage('Enregistré. Le nouveau taux s\'applique aux prochains retraits.');
        } catch (err) {
            setError(getErrorMessage(err, "Les frais n'ont pas pu être enregistrés."));
        } finally {
            setBusy(false);
        }
    }

    const example = Number(String(value).replace(',', '.'));
    const exampleFee = Number.isFinite(example) && example >= 0 ? Math.ceil((10000 * example) / 100) : null;

    return (
        <form className="section-card" onSubmit={save}>
            <h3 className="ad-h3">Frais de retrait</h3>
            <p className="empty-hint">
                Prélevés sur chaque retrait du portefeuille des revendeurs, pour couvrir les frais PayGate.
                {saved !== null && <> Taux actuel : <b>{saved} %</b>.</>}
            </p>
            <label className="field-label" htmlFor="ad-fee">Pourcentage (0 à {max})</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                    id="ad-fee"
                    className="text-input"
                    style={{ maxWidth: 120 }}
                    inputMode="decimal"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    disabled={saved === null}
                />
                <span>%</span>
                <button type="submit" className="btn-primary" disabled={busy || saved === null}>
                    {busy ? 'Enregistrement…' : 'Enregistrer'}
                </button>
            </div>
            {exampleFee !== null && (
                <p className="empty-hint">
                    Exemple : pour un retrait de 10 000 F, frais de {formatAmount(exampleFee)} F, le revendeur reçoit {formatAmount(10000 - exampleFee)} F.
                </p>
            )}
            {message && <p className="empty-hint">{message}</p>}
            {error && <p className="error-text">{error}</p>}
        </form>
    );
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
                            <small className="ad-muted">{formatAmount(stats.abonnements_mois)} F d'abonnements + {formatAmount(stats.frais_mois)} F de frais de vente + {formatAmount(stats.frais_retraits_mois || 0)} F de frais de retrait</small>
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
                    <WithdrawalFeeCard />
                </>
            )}
        </div>
    );
}
