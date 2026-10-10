import { useEffect, useState } from 'react';
import api from '../api/client';
import { Check, Clock } from 'lucide-react';
import Modal from './hotspot/Modal';
import { formatAmount } from '../utils/format';
import { getErrorMessage } from '../utils/errorMessage';

const NETWORKS = [
    { value: 'FLOOZ', label: 'Flooz' },
    { value: 'TMONEY', label: 'T-Money' },
];

function maskPhone(phone) {
    const digits = String(phone || '').replace(/\D/g, '').slice(-8);
    return digits.length >= 6 ? `${digits.slice(0, 2)} •• •• ${digits.slice(-2)}` : digits;
}

function networkLabel(value) {
    return NETWORKS.find((n) => n.value === value)?.label || value;
}

// Choix du numéro : ceux déjà utilisés, ou un autre (numéro + opérateur).
function NumberPicker({ numeros, choice, setChoice, phone, setPhone, network, setNetwork }) {
    return (
        <>
            {numeros.length > 0 && (
                <div className="wl-chips">
                    {numeros.map((n, i) => (
                        <button key={n.telephone} type="button" className={`wl-chip${choice === i ? ' is-on' : ''}`} onClick={() => setChoice(i)}>
                            {networkLabel(n.network)} {n.masque}
                        </button>
                    ))}
                    <button type="button" className={`wl-chip${choice === 'autre' ? ' is-on' : ''}`} onClick={() => setChoice('autre')}>
                        Autre numéro
                    </button>
                </div>
            )}
            {(choice === 'autre' || numeros.length === 0) && (
                <div className="wl-row">
                    <select className="text-input wl-network" value={network} onChange={(e) => setNetwork(e.target.value)} aria-label="Opérateur">
                        {NETWORKS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                    </select>
                    <input
                        className="text-input"
                        type="tel"
                        inputMode="numeric"
                        placeholder="90 00 00 00"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        aria-label="Numéro mobile money"
                    />
                </div>
            )}
        </>
    );
}

function useTarget(numeros) {
    const [choice, setChoice] = useState(numeros.length > 0 ? 0 : 'autre');
    const [phone, setPhone] = useState('');
    const [network, setNetwork] = useState('FLOOZ');
    const picked = typeof choice === 'number' ? numeros[choice] : null;
    const target = picked
        ? { telephone: picked.telephone, network: picked.network, label: `${networkLabel(picked.network)} ${picked.masque}` }
        : { telephone: phone.replace(/[\s.-]/g, ''), network, label: `${networkLabel(network)} ${maskPhone(phone)}` };
    const valid = /^\+?\d{8,15}$/.test(target.telephone);
    return { picker: { numeros, choice, setChoice, phone, setPhone, network, setNetwork }, target, valid };
}

function AmountPicker({ presets, value, setValue }) {
    const isPreset = presets.some((p) => p.value === value);
    return (
        <>
            <div className="wl-chips">
                {presets.map((p) => (
                    <button key={p.label} type="button" className={`wl-chip${value === p.value ? ' is-on' : ''}`} onClick={() => setValue(p.value)}>
                        {p.label}
                    </button>
                ))}
            </div>
            <input
                className="text-input wl-amount"
                type="number"
                min="1"
                step="1"
                placeholder="Autre montant"
                value={isPreset ? '' : (value || '')}
                onChange={(e) => setValue(e.target.value ? Number(e.target.value) : 0)}
                aria-label="Montant en FCFA"
            />
        </>
    );
}

export function WithdrawModal({ solde, numeros, onWithdraw, onClose }) {
    const { picker, target, valid } = useTarget(numeros);
    const [montant, setMontant] = useState(Math.min(10000, solde || 0) || 0);
    const [password, setPassword] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState(null);
    // Pourcentage de frais de retrait (réglé par MIABEWIFI). null = pas encore connu.
    const [feePercent, setFeePercent] = useState(null);

    useEffect(() => {
        api.get('/wallet/frais-retrait')
            .then((res) => setFeePercent(Number(res.data.pourcentage) || 0))
            .catch(() => setFeePercent(null));
    }, []);

    const frais = feePercent ? Math.ceil((montant * feePercent) / 100) : 0;
    const recu = montant - frais;

    const presets = [5000, 10000, 20000].filter((v) => v < solde).map((v) => ({ value: v, label: `${formatAmount(v)} F` }));
    if (solde > 0) presets.push({ value: solde, label: `Tout (${formatAmount(solde)} F)` });

    async function submit(e) {
        e.preventDefault();
        if (!valid) return setError('Choisissez ou saisissez un numéro mobile money valide.');
        if (!Number.isInteger(montant) || montant <= 0) return setError('Indiquez un montant en FCFA.');
        if (montant > solde) return setError('Le montant dépasse votre solde disponible.');
        if (recu <= 0) return setError('Montant trop faible une fois les frais déduits.');
        if (!password) return setError('Saisissez votre mot de passe pour confirmer.');
        setBusy(true);
        setError('');
        try {
            const data = await onWithdraw(target.telephone, target.network, montant, password);
            setResult(data);
        } catch (err) {
            setError(getErrorMessage(err, "Le retrait n'a pas pu être effectué."));
            setPassword('');
        } finally {
            setBusy(false);
        }
    }

    if (result) {
        const pending = result.statut === 'a_verifier';
        return (
            <Modal title={pending ? 'Retrait en vérification' : 'Retrait envoyé'} onClose={onClose}>
                <p className={pending ? 'wl-result is-warning' : 'wl-result'}>
                    {pending ? <Clock size={18} /> : <Check size={18} />}
                    {formatAmount(result.montant_recu ?? montant)} F vers {target.label}
                </p>
                {result.frais > 0 && (
                    <p className="empty-hint">Débité de votre solde : {formatAmount(result.montant)} F (dont {formatAmount(result.frais)} F de frais).</p>
                )}
                <p className="empty-hint">{result.message}</p>
                <div className="hs-modal-actions">
                    <button type="button" className="btn-primary" onClick={onClose}>Fermer</button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal title="Retirer vers mobile money" onClose={onClose}>
            <form onSubmit={submit}>
                <p className="field-label">Vers</p>
                <NumberPicker {...picker} />
                <p className="field-label wl-mt">Montant</p>
                <AmountPicker presets={presets} value={montant} setValue={setMontant} />
                {valid && montant > 0 && montant <= solde && (
                    <div className="wl-summary">
                        Vous recevrez <b>{formatAmount(recu)} F</b> sur {target.label}.
                        {frais > 0 && <span>Frais de retrait ({feePercent} %) : {formatAmount(frais)} F</span>}
                        <span>Solde après retrait : {formatAmount(solde - montant)} F</span>
                    </div>
                )}
                <label className="field-label wl-mt" htmlFor="wl-password">Votre mot de passe, pour confirmer</label>
                <input
                    id="wl-password"
                    className="text-input"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />
                {error && <p className="error-text wl-mt">{error}</p>}
                <div className="hs-modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>Annuler</button>
                    <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Envoi…' : 'Confirmer le retrait'}</button>
                </div>
            </form>
        </Modal>
    );
}

export function RechargeModal({ numeros, onRecharge, onClose }) {
    const { picker, target, valid } = useTarget(numeros);
    const [montant, setMontant] = useState(5000);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState(null);
    const presets = [1000, 2000, 5000, 10000].map((v) => ({ value: v, label: `${formatAmount(v)} F` }));

    async function submit(e) {
        e.preventDefault();
        if (!valid) return setError('Choisissez ou saisissez un numéro mobile money valide.');
        if (!Number.isInteger(montant) || montant <= 0) return setError('Indiquez un montant en FCFA.');
        setBusy(true);
        setError('');
        try {
            setResult(await onRecharge(target.telephone, target.network, montant));
        } catch (err) {
            setError(getErrorMessage(err, "La recharge n'a pas pu être lancée."));
        } finally {
            setBusy(false);
        }
    }

    if (result) {
        return (
            <Modal title="Validez sur votre téléphone" onClose={onClose}>
                <p className="wl-result"><Clock size={18} /> {formatAmount(montant)} F depuis {target.label}</p>
                <p className="empty-hint">
                    Une demande de paiement vient d'être envoyée sur ce numéro. Validez-la : votre solde sera crédité
                    dès la confirmation de l'opérateur.
                </p>
                <div className="hs-modal-actions">
                    <button type="button" className="btn-primary" onClick={onClose}>Fermer</button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal title="Recharger mon portefeuille" onClose={onClose}>
            <form onSubmit={submit}>
                <p className="field-label">Depuis</p>
                <NumberPicker {...picker} />
                <p className="field-label wl-mt">Montant</p>
                <AmountPicker presets={presets} value={montant} setValue={setMontant} />
                {error && <p className="error-text wl-mt">{error}</p>}
                <div className="hs-modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>Annuler</button>
                    <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Envoi…' : `Recharger ${montant > 0 ? `${formatAmount(montant)} F` : ''}`}</button>
                </div>
            </form>
        </Modal>
    );
}
