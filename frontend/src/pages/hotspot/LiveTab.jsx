import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Search, Smartphone } from 'lucide-react';
import api from '../../api/client';
import { confirmDialog } from '../../utils/confirm';
import { formatAmount } from '../../utils/format';
import { errorMessage, formatQuota } from './hotspotUtils';

const REFRESH_SECONDS = 30;

// 3725 -> « 1 h 2 min » ; 450000 -> « 5 j 5 h ».
export function formatSeconds(seconds) {
    if (seconds === null || seconds === undefined) return '';
    const s = Math.max(0, Math.round(seconds));
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (d > 0) return h ? `${d} j ${h} h` : `${d} j`;
    if (h > 0) return m ? `${h} h ${m} min` : `${h} h`;
    if (m > 0) return `${m} min`;
    return `${s} s`;
}

export function formatBytes(bytes) {
    const n = Number(bytes) || 0;
    if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1).replace('.', ',')} Go`;
    if (n >= 1024 ** 2) return `${Math.round(n / 1024 ** 2)} Mo`;
    if (n >= 1024) return `${Math.round(n / 1024)} Ko`;
    return `${n} o`;
}

function saleText(vente) {
    if (!vente) return 'Ticket non vendu par MIABEWIFI';
    if (vente.mode === 'en_ligne') {
        return `Payé en ligne${vente.reseau ? ` (${vente.reseau}${vente.telephone ? `, ${vente.telephone}` : ''})` : ''} · ${formatAmount(vente.montant)} F`;
    }
    return `Vendu au comptoir · ${formatAmount(vente.montant)} F`;
}

function remaining(c) {
    if (c.reste === null || c.reste === undefined) return { text: 'Sans limite de temps', pct: null };
    const total = c.limite || c.reste + c.depuis;
    const pct = total > 0 ? Math.max(2, Math.min(100, Math.round((c.reste / total) * 100))) : null;
    return { text: `Reste ${formatSeconds(c.reste)}`, pct };
}

// Onglet « En direct » : qui est connecté en ce moment, combien de temps il lui reste,
// ce qu'il consomme, avec la possibilité de le déconnecter.
export default function LiveTab({ routerId }) {
    const [data, setData] = useState(null);
    const [error, setError] = useState('');
    const [info, setInfo] = useState('');
    const [updatedAt, setUpdatedAt] = useState(null);
    const [now, setNow] = useState(Date.now());
    const [openId, setOpenId] = useState(null);
    const [search, setSearch] = useState('');
    const [busyId, setBusyId] = useState(null);
    const [loading, setLoading] = useState(false);

    const load = useCallback(() => {
        if (!routerId) return Promise.resolve();
        setLoading(true);
        return api.get(`/hotspot/${routerId}/live`)
            .then((res) => {
                setData(res.data);
                setError('');
                setUpdatedAt(Date.now());
            })
            .catch((err) => setError(errorMessage(err, 'Impossible de joindre le routeur.')))
            .finally(() => setLoading(false));
    }, [routerId]);

    useEffect(() => {
        setData(null);
        setInfo('');
        load();
        const refresh = setInterval(load, REFRESH_SECONDS * 1000);
        const tick = setInterval(() => setNow(Date.now()), 1000);
        return () => {
            clearInterval(refresh);
            clearInterval(tick);
        };
    }, [load]);

    async function disconnect(client) {
        if (!(await confirmDialog(
            `Déconnecter ${client.code} ? Il pourra se reconnecter avec son code tant que son forfait n'est pas épuisé.`,
            { confirmLabel: 'Déconnecter', danger: true },
        ))) return;
        setBusyId(client.id);
        setInfo('');
        try {
            await api.delete(`/hotspot/${routerId}/live/${encodeURIComponent(client.id)}`);
            setInfo(`${client.code} a été déconnecté.`);
            await load();
        } catch (err) {
            setError(errorMessage(err, 'Impossible de déconnecter ce client.'));
        } finally {
            setBusyId(null);
        }
    }

    const term = search.trim().toUpperCase();
    const clients = (data?.clients || []).filter((c) => !term || c.code.toUpperCase().includes(term));
    const ago = updatedAt ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null;

    return (
        <div className="hs-live">
            <div className="hs-stats">
                <div className="hs-stat"><span>Clients connectés</span><b>{data ? data.connectes : '—'}</b></div>
                <div className={`hs-stat${data?.bientot_finis ? ' is-warning' : ''}`}><span>Finissent dans moins de 15 min</span><b>{data ? data.bientot_finis : '—'}</b></div>
                <div className="hs-stat"><span>Données des clients connectés</span><b>{data ? formatBytes(data.octets_total) : '—'}</b></div>
                <div className="hs-stat"><span>Sur le Wi-Fi sans ticket</span><b>{data ? data.sans_ticket : '—'}</b></div>
            </div>

            <div className="hs-live-bar">
                <span className="empty-hint hs-no-margin">
                    {ago === null ? 'Connexion au routeur…' : `Mis à jour il y a ${formatSeconds(ago)} · actualisation automatique toutes les ${REFRESH_SECONDS} s`}
                </span>
                <div className="hs-inline">
                    <div className="hs-search">
                        <Search size={16} />
                        <input type="search" className="text-input" placeholder="Rechercher un code" value={search} onChange={(e) => setSearch(e.target.value)} />
                    </div>
                    <button type="button" className="btn-secondary hs-btn-sm" onClick={load} disabled={loading}>
                        <RefreshCw size={14} /> Actualiser
                    </button>
                </div>
            </div>

            {error && <p className="error-text">{error}</p>}
            {info && <p className="success-text">{info}</p>}

            {data && clients.length === 0 && (
                <div className="section-card"><p className="empty-hint hs-no-margin">
                    {term ? `Aucun client connecté avec un code contenant « ${search.trim()} ».` : 'Aucun client connecté pour le moment.'}
                </p></div>
            )}

            <div className="hs-groups">
                {clients.map((c) => {
                    const r = remaining(c);
                    const open = openId === c.id;
                    return (
                        <div key={c.id} className="section-card hs-live-row">
                            <div className="hs-live-head" role="button" tabIndex={0}
                                onClick={() => setOpenId(open ? null : c.id)}
                                onKeyDown={(e) => { if (e.key === 'Enter') setOpenId(open ? null : c.id); }}>
                                <div className="hs-live-icon"><Smartphone size={18} /></div>
                                <div className="hs-live-who">
                                    <div>
                                        <span className="mono hs-live-code">{c.code}</span>
                                        {c.bientot_fini && <span className="badge badge-warning">Bientôt fini</span>}
                                    </div>
                                    <span className="empty-hint hs-no-margin">
                                        {c.forfait || 'Forfait inconnu'}{c.quota_mo ? ` · ${formatQuota(c.quota_mo)}` : ''} · connecté depuis {formatSeconds(c.depuis)}
                                    </span>
                                </div>
                                <div className="hs-live-left">
                                    <span className="empty-hint hs-no-margin">{r.text}</span>
                                    {r.pct !== null && (
                                        <div className={`hs-bar hs-bar-thin${c.bientot_fini ? ' is-low' : ''}`}><i style={{ width: `${r.pct}%` }} /></div>
                                    )}
                                </div>
                                <span className="hs-live-data">{formatBytes(c.octets)}</span>
                                <button type="button" className="btn-secondary hs-btn-sm" disabled={busyId === c.id}
                                    onClick={(e) => { e.stopPropagation(); disconnect(c); }}>
                                    Déconnecter
                                </button>
                            </div>
                            {open && (
                                <div className="hs-live-details">
                                    <div><span>Ticket</span>{saleText(c.vente)}</div>
                                    <div><span>Appareil</span><span className="mono">{c.mac || '—'}</span></div>
                                    <div><span>Adresse sur le Wi-Fi</span><span className="mono">{c.adresse || '—'}</span></div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            {clients.length > 0 && <p className="empty-hint">Touchez un client pour voir le détail.</p>}
        </div>
    );
}
