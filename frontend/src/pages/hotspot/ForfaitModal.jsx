import { useState } from 'react';
import Modal from './Modal';
import { SPEEDS, durationParts, errorMessage } from './hotspotUtils';

// Création ou modification d'un forfait : ce qui est réglé sur le routeur (durée, vitesse,
// appareils) et ce qui sert à la vente (prix, validité, quota), dans un seul formulaire.
export default function ForfaitModal({ profile, setting, defaultRate, onSave, onClose }) {
    const editing = Boolean(profile);
    const parts = durationParts(profile?.['session-timeout']);
    const currentRate = profile?.['rate-limit'] || defaultRate || '2M/2M';
    const knownRate = SPEEDS.some((s) => s.value.toLowerCase() === currentRate.toLowerCase());

    const [name, setName] = useState(profile?.name || '');
    const [dureeValeur, setDureeValeur] = useState(parts.valeur || (editing ? '' : '1'));
    const [dureeUnite, setDureeUnite] = useState(parts.unite || 'h');
    const [rate, setRate] = useState(currentRate);
    const [partage, setPartage] = useState(String(profile?.['shared-users'] || '1'));
    const [prix, setPrix] = useState(setting?.prix ? String(setting.prix) : '');
    const [validite, setValidite] = useState(setting?.validite_jours ? String(setting.validite_jours) : '');
    const [quotaValeur, setQuotaValeur] = useState(setting?.quota_mo ? String(setting.quota_mo >= 1024 ? setting.quota_mo / 1024 : setting.quota_mo) : '');
    const [quotaUnite, setQuotaUnite] = useState(setting?.quota_mo && setting.quota_mo < 1024 ? 'mo' : 'go');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const suggestedName = dureeValeur ? `Ticket-${dureeValeur}${dureeUnite === 'd' ? 'j' : 'h'}` : '';

    async function handleSave(e) {
        e.preventDefault();
        const prixNum = Number(prix);
        if (!Number.isInteger(prixNum) || prixNum <= 0) {
            setError('Indiquez le prix d\'un ticket en FCFA (nombre entier).');
            return;
        }
        if (!dureeValeur || Number(dureeValeur) < 1) {
            setError('Indiquez la durée de connexion.');
            return;
        }
        const finalName = (name.trim() || suggestedName).trim();
        if (!editing && !/^[A-Za-z0-9 _-]{1,60}$/.test(finalName)) {
            setError('Le nom ne peut contenir que des lettres sans accents, chiffres, espaces, - et _.');
            return;
        }
        const quotaMo = quotaValeur ? Math.round(Number(quotaValeur) * (quotaUnite === 'go' ? 1024 : 1)) : null;
        if (quotaValeur && !(quotaMo >= 1)) {
            setError('Quota de données invalide.');
            return;
        }
        setBusy(true);
        setError('');
        try {
            await onSave({
                name: finalName,
                duree_valeur: Number(dureeValeur),
                duree_unite: dureeUnite,
                partage: Number(partage) || 1,
                rate_limit: rate,
                prix: prixNum,
                validite_jours: validite ? Number(validite) : null,
                quota_mo: quotaMo,
            });
        } catch (err) {
            setError(errorMessage(err, "Impossible d'enregistrer ce forfait."));
            setBusy(false);
        }
    }

    return (
        <Modal title={editing ? 'Modifier le forfait' : 'Nouveau forfait'} onClose={onClose} width={480}>
            <form onSubmit={handleSave}>
                <label className="field-label" htmlFor="hs-f-duree">Durée de connexion</label>
                <div style={{ display: 'flex', gap: 8 }}>
                    <input id="hs-f-duree" className="text-input hs-input-small" type="number" min="1" max="999" value={dureeValeur} onChange={(e) => setDureeValeur(e.target.value)} />
                    <select className="text-input hs-input-small" value={dureeUnite} onChange={(e) => setDureeUnite(e.target.value)} aria-label="Unité">
                        <option value="h">heure(s)</option>
                        <option value="d">jour(s)</option>
                    </select>
                </div>

                <label className="field-label hs-mt" htmlFor="hs-f-prix">Prix d'un ticket (FCFA)</label>
                <input id="hs-f-prix" className="text-input hs-input-small" type="number" min="1" step="1" value={prix} onChange={(e) => setPrix(e.target.value)} />

                <label className="field-label hs-mt" htmlFor="hs-f-vitesse">Vitesse par client</label>
                <select id="hs-f-vitesse" className="text-input" value={rate} onChange={(e) => setRate(e.target.value)}>
                    {SPEEDS.map((s) => <option key={s.value} value={s.value}>{s.label} ({s.hint})</option>)}
                    {!knownRate && <option value={currentRate}>Personnalisée ({currentRate})</option>}
                </select>

                <label className="field-label hs-mt" htmlFor="hs-f-partage">Nombre d'appareils pouvant utiliser le même ticket en même temps</label>
                <select id="hs-f-partage" className="text-input hs-input-small" value={partage} onChange={(e) => setPartage(e.target.value)}>
                    {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>

                <details className="hs-options">
                    <summary>Options : validité, quota de données, nom technique</summary>
                    <label className="field-label hs-mt" htmlFor="hs-f-validite">Valable combien de jours après la 1re connexion ? (vide = sans limite)</label>
                    <input id="hs-f-validite" className="text-input hs-input-small" type="number" min="1" max="365" value={validite} onChange={(e) => setValidite(e.target.value)} />

                    <label className="field-label hs-mt" htmlFor="hs-f-quota">Quota de données par ticket (vide = illimité)</label>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input id="hs-f-quota" className="text-input hs-input-small" type="number" min="1" value={quotaValeur} onChange={(e) => setQuotaValeur(e.target.value)} />
                        <select className="text-input hs-input-small" value={quotaUnite} onChange={(e) => setQuotaUnite(e.target.value)} aria-label="Unité du quota">
                            <option value="go">Go</option>
                            <option value="mo">Mo</option>
                        </select>
                    </div>

                    <label className="field-label hs-mt" htmlFor="hs-f-nom">Nom technique sur le routeur</label>
                    <input
                        id="hs-f-nom"
                        className="text-input"
                        value={editing ? profile.name : name}
                        placeholder={suggestedName}
                        disabled={editing}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <p className="empty-hint">{editing ? 'Le nom ne se modifie pas : les tickets déjà créés y restent rattachés.' : `Laissé vide, il sera nommé « ${suggestedName} ».`}</p>
                </details>

                {editing && (
                    <p className="empty-hint hs-mt">Les tickets déjà créés gardent leur durée d'origine ; les prochains utiliseront la nouvelle.</p>
                )}
                {error && <p className="error-text hs-mt">{error}</p>}
                <div className="hs-modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>Annuler</button>
                    <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer'}</button>
                </div>
            </form>
        </Modal>
    );
}
