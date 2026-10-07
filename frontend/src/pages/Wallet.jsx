import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowDownLeft, ArrowUpRight, ChevronLeft, ChevronRight, Clock, Download, Radio, Ticket } from 'lucide-react';
import { useWalletData } from '../hooks/useWalletData';
import { WithdrawModal, RechargeModal } from './WalletForms';
import './Wallet.css';
import { formatAmount } from '../utils/format';

const FILTERS = [
    { key: 'all', label: 'Tout' },
    { key: 'vente', label: 'Ventes' },
    { key: 'retrait', label: 'Retraits' },
    { key: 'recharge', label: 'Recharges' },
    { key: 'debit', label: 'Abonnements' },
];

const ICONS = { vente: Ticket, recharge: ArrowDownLeft, retrait: ArrowUpRight, debit: Radio };
const PENDING_BADGES = {
    a_verifier: { label: 'En vérification', cls: 'badge-warning' },
    en_attente: { label: 'En attente', cls: 'badge-warning' },
    echoue: { label: 'Échoué', cls: 'badge-danger' },
};
const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];

function monthLabel(mois) {
    const [y, m] = mois.split('-').map(Number);
    const label = `${MONTHS[m - 1]} ${y}`;
    return label.charAt(0).toUpperCase() + label.slice(1);
}

function shiftMonth(mois, delta) {
    const [y, m] = mois.split('-').map(Number);
    const d = new Date(y, m - 1 + delta, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function dayLabel(value) {
    const d = new Date(value);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const same = (a, b) => a.toDateString() === b.toDateString();
    if (same(d, today)) return "Aujourd'hui";
    if (same(d, yesterday)) return 'Hier';
    return d.toLocaleDateString('fr-FR');
}

function signed(value) {
    return `${value >= 0 ? '+' : '−'} ${formatAmount(Math.abs(value))} F`;
}

const PAGE = 30;

export default function Wallet() {
    const navigate = useNavigate();
    const {
        solde, mois, setMois, resume, historique, numeros, loading, error,
        recharger, retirer, telechargerReleve,
    } = useWalletData();
    const [modal, setModal] = useState(null); // 'retrait' | 'recharge'
    const [searchParams, setSearchParams] = useSearchParams();

    // Raccourci « Retirer » du tableau de bord : ouvre le retrait dès que le solde est connu.
    useEffect(() => {
        if (searchParams.get('action') !== 'retirer' || solde === null) return;
        if (solde > 0) setModal('retrait');
        setSearchParams({}, { replace: true });
    }, [searchParams, solde, setSearchParams]);
    const [filter, setFilter] = useState('all');
    const [shown, setShown] = useState(PAGE);
    const [downloadError, setDownloadError] = useState('');

    const thisMonth = useMemo(() => {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    }, []);

    const filtered = historique.filter((t) => filter === 'all' || t.type === filter);
    const visible = filtered.slice(0, shown);
    let lastDay = '';

    async function handleDownload() {
        setDownloadError('');
        try {
            await telechargerReleve();
        } catch {
            setDownloadError('Impossible de télécharger le relevé pour le moment.');
        }
    }

    return (
        <div className="wl-page">
            <h1 className="page-title">Portefeuille</h1>
            {error && <p className="error-text">{error}</p>}

            <div className="wl-top">
                <div className="section-card">
                    <span className="wl-label">Solde disponible</span>
                    <div className="wl-balance">{solde === null ? '--' : formatAmount(solde)} <small>F</small></div>
                    {resume?.reserve > 0 && (
                        <span className="wl-reserved">
                            <Clock size={13} /> {formatAmount(resume.reserve)} F réservés : retrait en vérification
                        </span>
                    )}
                    <div className="wl-actions">
                        <button type="button" className="btn-primary" onClick={() => setModal('retrait')} disabled={!solde}>
                            <ArrowUpRight size={16} /> Retirer
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => setModal('recharge')}>
                            <ArrowDownLeft size={16} /> Recharger
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => navigate('/routers')}>
                            <Radio size={16} /> Payer un abonnement
                        </button>
                    </div>
                </div>

                <div className="section-card">
                    <div className="wl-month">
                        <button type="button" className="icon-btn" onClick={() => setMois(shiftMonth(mois, -1))} aria-label="Mois précédent">
                            <ChevronLeft size={18} />
                        </button>
                        <span className="wl-label">{monthLabel(mois)}</span>
                        <button type="button" className="icon-btn" onClick={() => setMois(shiftMonth(mois, 1))} disabled={mois >= thisMonth} aria-label="Mois suivant">
                            <ChevronRight size={18} />
                        </button>
                    </div>
                    {resume ? (
                        <>
                            <div className="wl-line"><span>Ventes en ligne</span><b className="wl-in">{signed(resume.ventes)}</b></div>
                            <div className="wl-line"><span>Frais MIABEWIFI</span><b>{signed(-resume.frais)}</b></div>
                            <div className="wl-line"><span>Recharges</span><b className="wl-in">{signed(resume.recharges)}</b></div>
                            <div className="wl-line"><span>Abonnements payés</span><b>{signed(-resume.abonnements)}</b></div>
                            <div className="wl-line"><span>Retraits</span><b>{signed(-resume.retraits)}</b></div>
                            {resume.ajustements ? (
                                <div className="wl-line"><span>Corrections de solde</span><b className={resume.ajustements > 0 ? 'wl-in' : ''}>{signed(resume.ajustements)}</b></div>
                            ) : null}
                        </>
                    ) : (
                        <p className="empty-hint">Chargement du bilan…</p>
                    )}
                </div>
            </div>

            <div className="section-card">
                <div className="wl-history-head">
                    <div className="wl-chips">
                        {FILTERS.map((f) => (
                            <button key={f.key} type="button" className={`wl-chip${filter === f.key ? ' is-on' : ''}`}
                                onClick={() => { setFilter(f.key); setShown(PAGE); }}>
                                {f.label}
                            </button>
                        ))}
                    </div>
                    <button type="button" className="btn-secondary wl-small" onClick={handleDownload} disabled={historique.length === 0}>
                        <Download size={14} /> Télécharger le relevé
                    </button>
                </div>
                {downloadError && <p className="error-text">{downloadError}</p>}

                {loading && <p className="empty-hint">Chargement…</p>}
                {!loading && filtered.length === 0 && (
                    <p className="empty-hint">
                        {filter === 'all'
                            ? 'Aucune opération pour le moment. Vos ventes en ligne apparaîtront ici.'
                            : 'Aucune opération de ce type.'}
                    </p>
                )}

                {visible.map((t) => {
                    const day = dayLabel(t.created_at);
                    const header = day !== lastDay ? <div className="wl-day">{day}</div> : null;
                    lastDay = day;
                    const Icon = ICONS[t.type] || Ticket;
                    const badge = PENDING_BADGES[t.statut];
                    const counted = !(t.statut === 'echoue' || (t.statut === 'en_attente' && t.type === 'recharge'));
                    return (
                        <div key={t.id}>
                            {header}
                            <div className="wl-tx">
                                <div className={`wl-tx-icon${t.montant_signe > 0 ? ' is-in' : ''}`}><Icon size={16} /></div>
                                <div className="wl-tx-text">
                                    <div>
                                        {t.titre}
                                        {badge && <span className={`badge ${badge.cls} wl-badge`}>{badge.label}</span>}
                                    </div>
                                    {t.detail && <span className="wl-tx-detail">{t.detail}</span>}
                                </div>
                                <b className={`wl-tx-amount${t.montant_signe > 0 ? ' wl-in' : ''}${counted ? '' : ' is-void'}`}>
                                    {signed(t.montant_signe)}
                                </b>
                            </div>
                        </div>
                    );
                })}

                {filtered.length > shown && (
                    <button type="button" className="btn-secondary wl-more" onClick={() => setShown((n) => n + PAGE)}>
                        Voir plus d'opérations
                    </button>
                )}
            </div>

            {modal === 'retrait' && (
                <WithdrawModal solde={solde || 0} numeros={numeros} onWithdraw={retirer} onClose={() => setModal(null)} />
            )}
            {modal === 'recharge' && (
                <RechargeModal numeros={numeros} onRecharge={recharger} onClose={() => setModal(null)} />
            )}
        </div>
    );
}
