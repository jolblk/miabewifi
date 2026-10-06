import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import Modal from './Modal';
import { errorMessage, groupLabel } from './hotspotUtils';
import { formatAmount } from '../../utils/format';

// Vente au comptoir : on choisit le forfait, le prochain code libre s'affiche en grand,
// et un clic le marque vendu une fois l'argent encaissé.
export default function SellTicketModal({ groups, initialKey, onSell, onClose }) {
    const sellable = groups.filter((g) => g.disponibles > 0);
    const [selectedKey, setSelectedKey] = useState(
        sellable.some((g) => g.key === initialKey) ? initialKey : sellable[0]?.key || null,
    );
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [sold, setSold] = useState(null);
    const [copied, setCopied] = useState(false);

    const group = sellable.find((g) => g.key === selectedKey) || null;
    const voucher = group?.nextVoucher || null;

    async function handleSell() {
        if (!voucher) return;
        setBusy(true);
        setError('');
        try {
            await onSell(voucher.id);
            setSold({ code: voucher.code, label: groupLabel(group), prix: group.prix });
        } catch (err) {
            setError(errorMessage(err, "Impossible d'enregistrer la vente."));
        } finally {
            setBusy(false);
        }
    }

    function handleCopy(code) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(code).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
            }).catch(() => {});
        }
    }

    if (sold) {
        return (
            <Modal title="Ticket vendu" onClose={onClose}>
                <p className="hs-success-line"><Check size={18} /> Vente enregistrée : {sold.label}, {formatAmount(sold.prix)} FCFA.</p>
                <div className="hs-big-code">{sold.code}</div>
                <p className="empty-hint">Donnez ce code au client : il le tape sur la page du Wi-Fi.</p>
                <div className="hs-modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose}>Fermer</button>
                    <button type="button" className="btn-primary" onClick={() => setSold(null)}>Vendre un autre ticket</button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal title="Vendre un ticket" onClose={onClose}>
            {sellable.length === 0 ? (
                <p className="empty-hint">Plus aucun ticket disponible. Créez-en de nouveaux pour pouvoir vendre.</p>
            ) : (
                <>
                    <p className="field-label">1. Quel forfait le client achète-t-il ?</p>
                    <div className="hs-choices">
                        {sellable.map((g) => (
                            <button
                                key={g.key}
                                type="button"
                                className={`hs-choice${g.key === selectedKey ? ' is-on' : ''}`}
                                onClick={() => setSelectedKey(g.key)}
                            >
                                <strong>{groupLabel(g)}</strong>
                                <span>{formatAmount(g.prix)} F · {g.disponibles} dispo.</span>
                            </button>
                        ))}
                    </div>

                    {voucher && (
                        <>
                            <p className="field-label" style={{ marginTop: 16 }}>2. Code à donner au client</p>
                            <div className="hs-big-code">{voucher.code}</div>
                            <div style={{ textAlign: 'center' }}>
                                <button type="button" className="hs-link" onClick={() => handleCopy(voucher.code)}>
                                    <Copy size={14} /> {copied ? 'Copié !' : 'Copier le code'}
                                </button>
                            </div>
                        </>
                    )}

                    {error && <p className="error-text" style={{ marginTop: 12 }}>{error}</p>}

                    <div className="hs-modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
                        <button type="button" className="btn-primary" disabled={busy || !voucher} onClick={handleSell}>
                            <Check size={16} /> Encaissé ({formatAmount(group?.prix)} F), marquer vendu
                        </button>
                    </div>
                </>
            )}
        </Modal>
    );
}
