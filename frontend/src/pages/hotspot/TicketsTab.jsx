import { useState } from 'react';
import { Check, Download, Eye, Plus, Search, Ticket, Trash2 } from 'lucide-react';
import { confirmDialog } from '../../utils/confirm';
import { formatAmount, formatDate } from '../../utils/format';
import { errorMessage, groupLabel, isAvailable, isLowStock, ticketBadges } from './hotspotUtils';

function StockBar({ group }) {
    const ratio = group.total ? Math.round((group.disponibles / group.total) * 100) : 0;
    return (
        <div className={`hs-bar${isLowStock(group) || group.disponibles === 0 ? ' is-low' : ''}`}>
            <i style={{ width: `${ratio}%` }} />
        </div>
    );
}

function CodeChip({ voucher, busy, onSell, onDelete }) {
    return (
        <div className={`hs-code${isAvailable(voucher) ? '' : ' is-off'}`}>
            <span className="mono">{voucher.code}</span>
            {ticketBadges(voucher).map((b) => (
                <span key={b.label} className={`badge ${b.cls}`}>{b.label}</span>
            ))}
            {isAvailable(voucher) && (
                <button type="button" className="hs-mini-btn" disabled={busy} onClick={() => onSell(voucher)}>
                    <Check size={12} /> Vendre
                </button>
            )}
            {voucher.statut !== 'USED' && !voucher.sale && (
                <button type="button" className="icon-btn" disabled={busy} onClick={() => onDelete(voucher)} aria-label={`Supprimer le ticket ${voucher.code}`}>
                    <Trash2 size={13} />
                </button>
            )}
        </div>
    );
}

export default function TicketsTab({
    groups, batches, loading, busy, setBusy, onMessage,
    onOpenSell, onOpenWizard, onSellVoucher, onDeleteVoucher, onDeleteBatch, onDownload, onSetGroupOnline,
}) {
    const [openKey, setOpenKey] = useState(null);
    const [search, setSearch] = useState('');

    const term = search.trim().toUpperCase();
    const results = term.length >= 3
        ? batches.flatMap((b) => (b.vouchers || [])
            .filter((v) => v.code.toUpperCase().includes(term))
            .map((v) => ({ voucher: v, group: groups.find((g) => g.batches.some((x) => x.id === b.id)) })))
            .slice(0, 20)
        : [];

    async function run(action, fallback) {
        setBusy(true);
        onMessage('', '');
        try {
            const info = await action();
            if (info) onMessage('', info);
        } catch (err) {
            onMessage(errorMessage(err, fallback), '');
        } finally {
            setBusy(false);
        }
    }

    async function sellOne(voucher) {
        if (!(await confirmDialog(`Marquer le ticket ${voucher.code} comme vendu ?`, { confirmLabel: 'Marquer vendu' }))) return;
        run(async () => { await onSellVoucher(voucher.id); return `Ticket ${voucher.code} marqué vendu.`; }, 'Impossible d\'enregistrer la vente.');
    }

    async function deleteOne(voucher) {
        if (!(await confirmDialog(`Supprimer le ticket ${voucher.code} ? Il ne pourra plus être utilisé.`, { confirmLabel: 'Supprimer', danger: true }))) return;
        run(async () => { await onDeleteVoucher(voucher.id); return `Ticket ${voucher.code} supprimé.`; }, 'Impossible de supprimer ce ticket.');
    }

    async function deleteBatch(batch) {
        if (!(await confirmDialog(`Supprimer ce lot de ${batch.quantite} tickets ? Les tickets déjà vendus sont conservés, les autres sont définitivement supprimés.`, { confirmLabel: 'Supprimer', danger: true }))) return;
        run(async () => {
            const res = await onDeleteBatch(batch.id);
            return res.supprimes > 0
                ? `${res.supprimes} ticket(s) supprimé(s)${res.conserves_vendus ? `, ${res.conserves_vendus} conservé(s) (déjà vendus)` : ''}.`
                : 'Aucun ticket supprimé : tous ont déjà été vendus.';
        }, 'Impossible de supprimer ce lot.');
    }

    function print(group) {
        if (group.batches.length === 1) {
            run(async () => { await onDownload(group.batches[0].id); }, 'Impossible de télécharger le PDF.');
        } else {
            setOpenKey(group.key);
        }
    }

    if (!loading && groups.length === 0) {
        return (
            <div className="section-card hs-empty">
                <Ticket size={28} />
                <h2>Aucun ticket pour ce routeur</h2>
                <p className="empty-hint">Créez vos premiers tickets : choisissez un forfait, la quantité, puis imprimez-les.</p>
                <button type="button" className="btn-primary" onClick={() => onOpenWizard()}>
                    <Plus size={16} /> Créer mes premiers tickets
                </button>
            </div>
        );
    }

    return (
        <div>
            <div className="hs-search">
                <Search size={16} />
                <input
                    type="search"
                    className="text-input"
                    placeholder="Un client a un souci ? Recherchez son code"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {term.length >= 3 && (
                <div className="section-card hs-results">
                    {results.length === 0 ? (
                        <p className="empty-hint">Aucun ticket ne correspond à « {search.trim()} ».</p>
                    ) : results.map(({ voucher, group }) => (
                        <div key={voucher.id} className="hs-result-row">
                            <CodeChip voucher={voucher} busy={busy} onSell={sellOne} onDelete={deleteOne} />
                            <span className="empty-hint">{group ? `${groupLabel(group)} · ${formatAmount(group.prix)} F` : ''}</span>
                        </div>
                    ))}
                </div>
            )}

            {loading && groups.length === 0 && <p className="empty-hint">Chargement des tickets…</p>}

            <div className="hs-groups">
                {groups.map((g) => {
                    const open = openKey === g.key;
                    return (
                        <div key={g.key} className="section-card hs-group">
                            <div className="hs-group-head">
                                <div className="hs-group-title">
                                    <strong>{groupLabel(g)}</strong>
                                    <span className="hs-price">{formatAmount(g.prix)} F</span>
                                    {g.disponibles === 0
                                        ? <span className="badge badge-danger">Épuisé</span>
                                        : isLowStock(g) && <span className="badge badge-warning">Stock bas</span>}
                                </div>
                                <div className="hs-group-actions">
                                    <button type="button" className="btn-primary hs-btn-sm" disabled={busy || g.disponibles === 0} onClick={() => onOpenSell(g.key)}>
                                        <Check size={14} /> Vendre
                                    </button>
                                    <button type="button" className="btn-secondary hs-btn-sm" onClick={() => print(g)}>
                                        <Download size={14} /> Imprimer
                                    </button>
                                    <button type="button" className="btn-secondary hs-btn-sm" onClick={() => setOpenKey(open ? null : g.key)}>
                                        <Eye size={14} /> {open ? 'Masquer les codes' : 'Voir les codes'}
                                    </button>
                                    {(isLowStock(g) || g.disponibles === 0) && (
                                        <button type="button" className="btn-secondary hs-btn-sm" onClick={() => onOpenWizard(g.profile_name)}>
                                            <Plus size={14} /> Recréer des tickets
                                        </button>
                                    )}
                                </div>
                            </div>

                            <StockBar group={g} />
                            <div className="hs-group-foot">
                                <span className="empty-hint">
                                    {g.disponibles} disponible{g.disponibles > 1 ? 's' : ''} sur {g.total}
                                    {' · '}{g.vendus} vendu{g.vendus > 1 ? 's' : ''}
                                    {g.expires ? ` · ${g.expires} expiré${g.expires > 1 ? 's' : ''}` : ''}
                                </span>
                                <label className="hs-toggle-line hs-toggle-inline">
                                    <input
                                        type="checkbox"
                                        checked={g.online}
                                        disabled={busy}
                                        onChange={(e) => run(() => onSetGroupOnline(g, e.target.checked), 'Impossible de modifier la vente en ligne.')}
                                    />
                                    Vendu en ligne
                                </label>
                            </div>

                            {open && (
                                <div className="hs-batches">
                                    {g.batches.map((b) => (
                                        <div key={b.id} className="hs-batch">
                                            <div className="hs-batch-head">
                                                <span>Lot du {formatDate(b.created_at)} · {b.quantite} tickets</span>
                                                <div className="hs-group-actions">
                                                    <button type="button" className="btn-secondary hs-btn-sm" onClick={() => run(async () => { await onDownload(b.id); }, 'Impossible de télécharger le PDF.')}>
                                                        <Download size={14} /> PDF
                                                    </button>
                                                    <button type="button" className="btn-secondary hs-btn-sm router-menu-danger" disabled={busy} onClick={() => deleteBatch(b)}>
                                                        <Trash2 size={14} /> Supprimer le lot
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="hs-codes">
                                                {(b.vouchers || []).map((v) => (
                                                    <CodeChip key={v.id} voucher={v} busy={busy} onSell={sellOne} onDelete={deleteOne} />
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
