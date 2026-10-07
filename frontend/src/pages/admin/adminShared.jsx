import { useState } from 'react';
import api from '../../api/client';
import Modal from '../hotspot/Modal';
import { confirmDialog } from '../../utils/confirm';
import { getErrorMessage } from '../../utils/errorMessage';
import { formatDate } from '../../utils/format';

export const KIND = {
    abonnement: { label: 'Abonné', cls: 'badge-success' },
    offert: { label: 'Offert', cls: 'badge-neutral' },
    essai: { label: 'Essai', cls: 'badge-warning' },
    expire: { label: 'Expiré', cls: 'badge-danger' },
    aucun: { label: 'À activer', cls: 'badge-warning' },
};

export function isActiveKind(kind) {
    return kind === 'abonnement' || kind === 'offert' || kind === 'essai';
}

// Point de couleur : vert = en ligne et actif, orange = l'un des deux manque, rouge = les deux.
export function routerDot(r) {
    const active = isActiveKind(r.abonnement);
    if (r.is_connected && active) return 'green';
    if (r.is_connected || active) return 'orange';
    return 'red';
}

export function subscriptionLine(r) {
    if (r.abonnement === 'abonnement' || r.abonnement === 'offert') return `jusqu'au ${formatDate(r.subscription_expires_at)}`;
    if (r.abonnement === 'essai') return `essai jusqu'au ${formatDate(r.trial_expires_at)}`;
    if (r.abonnement === 'expire') return `terminé le ${formatDate(r.subscription_expires_at || r.trial_expires_at)}`;
    return 'jamais activé';
}

const DURATIONS = [
    { jours: 7, label: '7 jours' },
    { jours: 30, label: '1 mois' },
    { jours: 90, label: '3 mois' },
    { jours: 365, label: '1 an' },
];

// Offrir (activer ou prolonger) l'abonnement d'un routeur, ou l'arrêter.
export function SubscriptionModal({ router, onDone, onClose }) {
    const [jours, setJours] = useState(30);
    const [autre, setAutre] = useState('');
    const [motif, setMotif] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const active = isActiveKind(router.abonnement);
    const finalJours = autre ? Number(autre) : jours;

    async function offer() {
        if (!Number.isInteger(finalJours) || finalJours < 1 || finalJours > 3650) {
            setError('Indiquez une durée entre 1 et 3650 jours.');
            return;
        }
        setBusy(true);
        setError('');
        try {
            await api.post(`/admin/routers/${router.id}/offrir`, { jours: finalJours, motif: motif.trim() || null });
            onDone(`${finalJours} jours offerts à ${router.nom}.`);
        } catch (err) {
            setError(getErrorMessage(err, "L'abonnement n'a pas pu être activé."));
            setBusy(false);
        }
    }

    async function stop() {
        if (!(await confirmDialog(`Arrêter tout de suite l'abonnement de ${router.nom} ? Rien n'est remboursé, et la vente en ligne s'arrête.`, { confirmLabel: 'Arrêter', danger: true }))) return;
        setBusy(true);
        setError('');
        try {
            await api.post(`/admin/routers/${router.id}/arreter`);
            onDone(`Abonnement de ${router.nom} arrêté.`);
        } catch (err) {
            setError(getErrorMessage(err, "L'abonnement n'a pas pu être arrêté."));
            setBusy(false);
        }
    }

    return (
        <Modal title={`Abonnement · ${router.nom}`} onClose={onClose}>
            <p className="empty-hint">
                {active ? `Actuellement : ${subscriptionLine(router)}. Les jours offerts s'ajoutent à la suite.` : "Ce routeur n'a pas d'abonnement en cours."}
                {' '}Le revendeur n'est pas débité ; l'opération apparaît dans son historique comme « Abonnement offert ».
            </p>
            <div className="ad-chips">
                {DURATIONS.map((d) => (
                    <button key={d.jours} type="button" className={`wl-chip${!autre && jours === d.jours ? ' is-on' : ''}`}
                        onClick={() => { setJours(d.jours); setAutre(''); }}>
                        {d.label}
                    </button>
                ))}
            </div>
            <input className="text-input ad-input" type="number" min="1" max="3650" placeholder="Autre durée (en jours)" value={autre} onChange={(e) => setAutre(e.target.value)} />
            <label className="field-label ad-mt" htmlFor="ad-motif">Motif (facultatif)</label>
            <input id="ad-motif" className="text-input ad-input" maxLength={200} placeholder="Geste commercial, test, partenaire…" value={motif} onChange={(e) => setMotif(e.target.value)} />
            {error && <p className="error-text ad-mt">{error}</p>}
            <div className="hs-modal-actions">
                {active && <button type="button" className="btn-secondary router-menu-danger" disabled={busy} onClick={stop}>Arrêter l'abonnement</button>}
                <button type="button" className="btn-secondary" disabled={busy} onClick={onClose}>Annuler</button>
                <button type="button" className="btn-primary" disabled={busy} onClick={offer}>
                    {active ? `Prolonger de ${finalJours || '…'} jours` : `Offrir ${finalJours || '…'} jours`}
                </button>
            </div>
        </Modal>
    );
}
