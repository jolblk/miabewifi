import { useState } from 'react';
import { Check, Download, Plus } from 'lucide-react';
import Modal from './Modal';
import { errorMessage, forfaitTitle, formatQuota, humanDuration, speedLabel } from './hotspotUtils';
import { formatAmount } from '../../utils/format';

const QUANTITIES = [10, 20, 50, 100];

// Prix et options d'un forfait : ceux enregistrés, sinon ceux du dernier lot de ce forfait.
function defaultsFor(profileName, forfaitSettings, groups) {
    const setting = forfaitSettings.find((s) => s.profile_name === profileName);
    if (setting) return { prix: setting.prix, validite_jours: setting.validite_jours, quota_mo: setting.quota_mo, saved: true };
    const last = [...groups].reverse().find((g) => g.profile_name === profileName);
    if (last) return { prix: last.prix, validite_jours: last.validite_jours, quota_mo: last.quota_mo, saved: false };
    return { prix: '', validite_jours: null, quota_mo: null, saved: false };
}

function Steps({ step }) {
    return (
        <div className="hs-steps" aria-label={`Étape ${step} sur 3`}>
            {[1, 2, 3].map((n) => <i key={n} className={n <= step ? 'is-on' : ''} />)}
        </div>
    );
}

// Création de tickets en 3 étapes : forfait, quantité (et prix), puis impression.
export default function CreateTicketsWizard({
    profiles, forfaitSettings, groups, initialProfileName, onlineSalesEnabled,
    onCreate, onSavePrice, onSetOnline, onDownload, onNewForfait, onClose,
}) {
    const [step, setStep] = useState(initialProfileName ? 2 : 1);
    const [profileName, setProfileName] = useState(initialProfileName || '');
    const initial = defaultsFor(initialProfileName || '', forfaitSettings, groups);
    const [prix, setPrix] = useState(String(initial.prix || ''));
    const [validite, setValidite] = useState(initial.validite_jours ? String(initial.validite_jours) : '');
    const [quotaValeur, setQuotaValeur] = useState(initial.quota_mo ? String(initial.quota_mo >= 1024 ? initial.quota_mo / 1024 : initial.quota_mo) : '');
    const [quotaUnite, setQuotaUnite] = useState(initial.quota_mo && initial.quota_mo < 1024 ? 'mo' : 'go');
    const [quantite, setQuantite] = useState(20);
    const [autreQuantite, setAutreQuantite] = useState('');
    const [showOptions, setShowOptions] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [created, setCreated] = useState(null);
    const [online, setOnline] = useState(true);

    const sortedProfiles = [...profiles].sort((a, b) => {
        const pa = forfaitSettings.find((s) => s.profile_name === a.name)?.prix ?? Infinity;
        const pb = forfaitSettings.find((s) => s.profile_name === b.name)?.prix ?? Infinity;
        return pa - pb || String(a.name).localeCompare(String(b.name));
    });
    const profile = profiles.find((p) => p.name === profileName);
    const title = forfaitTitle(profileName, profiles);

    function chooseProfile(name) {
        const d = defaultsFor(name, forfaitSettings, groups);
        setProfileName(name);
        setPrix(d.prix ? String(d.prix) : '');
        setValidite(d.validite_jours ? String(d.validite_jours) : '');
        setQuotaValeur(d.quota_mo ? String(d.quota_mo >= 1024 ? d.quota_mo / 1024 : d.quota_mo) : '');
        setQuotaUnite(d.quota_mo && d.quota_mo < 1024 ? 'mo' : 'go');
        setStep(2);
    }

    const finalQuantite = autreQuantite ? Number(autreQuantite) : quantite;

    async function handleCreate() {
        const prixNum = Number(prix);
        if (!Number.isInteger(prixNum) || prixNum <= 0) {
            setError('Indiquez un prix en FCFA (nombre entier).');
            return;
        }
        if (!Number.isInteger(finalQuantite) || finalQuantite < 1 || finalQuantite > 500) {
            setError('La quantité doit être comprise entre 1 et 500.');
            return;
        }
        const quotaMo = quotaValeur ? Math.round(Number(quotaValeur) * (quotaUnite === 'go' ? 1024 : 1)) : null;
        if (quotaValeur && !(quotaMo >= 1)) {
            setError('Quota de données invalide.');
            return;
        }
        const validiteJours = validite ? Number(validite) : null;
        setBusy(true);
        setError('');
        try {
            const d = defaultsFor(profileName, forfaitSettings, groups);
            if (!d.saved || d.prix !== prixNum || (d.validite_jours || null) !== validiteJours || (d.quota_mo || null) !== quotaMo) {
                await onSavePrice(profileName, { prix: prixNum, validite_jours: validiteJours, quota_mo: quotaMo });
            }
            const batch = await onCreate({ profile_name: profileName, prix: prixNum, quantite: finalQuantite, validite_jours: validiteJours, quota_mo: quotaMo });
            setCreated(batch);
            setOnline(batch?.online_sale !== false);
            setStep(3);
        } catch (err) {
            setError(errorMessage(err, 'Impossible de créer les tickets.'));
        } finally {
            setBusy(false);
        }
    }

    async function toggleOnline(value) {
        if (!created) return;
        setOnline(value);
        try {
            await onSetOnline(created.id, value);
        } catch (err) {
            setOnline(!value);
            setError(errorMessage(err, 'Impossible de modifier la vente en ligne.'));
        }
    }

    return (
        <Modal title="Créer des tickets" onClose={onClose} width={480}>
            <Steps step={step} />

            {step === 1 && (
                <>
                    <p className="field-label">1. Quel forfait ?</p>
                    {sortedProfiles.length === 0 ? (
                        <p className="empty-hint">Aucun forfait sur ce routeur pour le moment.</p>
                    ) : (
                        <div className="hs-choices">
                            {sortedProfiles.map((p) => {
                                const s = forfaitSettings.find((x) => x.profile_name === p.name);
                                return (
                                    <button
                                        key={p['.id'] || p.name}
                                        type="button"
                                        className={`hs-choice${p.name === profileName ? ' is-on' : ''}`}
                                        onClick={() => chooseProfile(p.name)}
                                    >
                                        <strong>{humanDuration(p['session-timeout']) || p.name}</strong>
                                        <span>{s ? `${formatAmount(s.prix)} F` : 'Prix à définir'}</span>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                    <button type="button" className="hs-link" style={{ marginTop: 12 }} onClick={onNewForfait}>
                        <Plus size={14} /> Créer un nouveau forfait
                    </button>
                    <div className="hs-modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
                    </div>
                </>
            )}

            {step === 2 && (
                <>
                    <p className="field-label">2. Combien de tickets « {title} » ?</p>
                    <div className="hs-choices hs-choices-4">
                        {QUANTITIES.map((q) => (
                            <button
                                key={q}
                                type="button"
                                className={`hs-choice${!autreQuantite && q === quantite ? ' is-on' : ''}`}
                                onClick={() => { setQuantite(q); setAutreQuantite(''); }}
                            >
                                <strong>{q}</strong>
                                <span>tickets</span>
                            </button>
                        ))}
                    </div>
                    <input
                        className="text-input hs-input-small"
                        type="number"
                        min="1"
                        max="500"
                        placeholder="Autre quantité"
                        value={autreQuantite}
                        onChange={(e) => setAutreQuantite(e.target.value)}
                        style={{ marginTop: 8 }}
                    />

                    <label className="field-label" htmlFor="hs-wizard-prix" style={{ marginTop: 14 }}>Prix d'un ticket (FCFA)</label>
                    <input
                        id="hs-wizard-prix"
                        className="text-input hs-input-small"
                        type="number"
                        min="1"
                        step="1"
                        value={prix}
                        onChange={(e) => setPrix(e.target.value)}
                    />

                    <p className="empty-hint" style={{ marginTop: 10 }}>
                        {humanDuration(profile?.['session-timeout']) ? `${humanDuration(profile['session-timeout'])} de connexion` : 'Durée définie par le forfait'}
                        {profile ? ` · ${speedLabel(profile['rate-limit'])}` : ''}
                        {validite ? ` · valable ${validite} jours après la 1re connexion` : ''}
                        {quotaValeur ? ` · ${formatQuota(Math.round(Number(quotaValeur) * (quotaUnite === 'go' ? 1024 : 1)))} de données` : ''}
                    </p>

                    <button type="button" className="hs-link" onClick={() => setShowOptions((v) => !v)}>
                        {showOptions ? 'Masquer les options' : 'Options : validité et quota de données'}
                    </button>
                    {showOptions && (
                        <div className="hs-options">
                            <label className="field-label" htmlFor="hs-wizard-validite">Valable combien de jours après la 1re connexion ? (vide = sans limite)</label>
                            <input
                                id="hs-wizard-validite"
                                className="text-input hs-input-small"
                                type="number"
                                min="1"
                                max="365"
                                value={validite}
                                onChange={(e) => setValidite(e.target.value)}
                            />
                            <label className="field-label" htmlFor="hs-wizard-quota" style={{ marginTop: 10 }}>Quota de données par ticket (vide = illimité)</label>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <input
                                    id="hs-wizard-quota"
                                    className="text-input hs-input-small"
                                    type="number"
                                    min="1"
                                    value={quotaValeur}
                                    onChange={(e) => setQuotaValeur(e.target.value)}
                                />
                                <select className="text-input hs-input-small" value={quotaUnite} onChange={(e) => setQuotaUnite(e.target.value)}>
                                    <option value="go">Go</option>
                                    <option value="mo">Mo</option>
                                </select>
                            </div>
                        </div>
                    )}

                    {error && <p className="error-text" style={{ marginTop: 12 }}>{error}</p>}
                    <div className="hs-modal-actions">
                        <button type="button" className="btn-secondary" onClick={() => setStep(1)} disabled={busy}>Retour</button>
                        <button type="button" className="btn-primary" onClick={handleCreate} disabled={busy}>
                            {busy ? 'Création…' : `Créer ${finalQuantite || ''} tickets`}
                        </button>
                    </div>
                </>
            )}

            {step === 3 && created && (
                <>
                    <p className="hs-success-line"><Check size={18} /> 3. C'est prêt : {created.quantite} tickets « {title} » à {formatAmount(created.prix_unitaire)} F.</p>
                    <button type="button" className="btn-primary hs-wide" onClick={() => onDownload(created.id)}>
                        <Download size={16} /> Imprimer les tickets (PDF)
                    </button>
                    <label className="hs-toggle-line">
                        <input type="checkbox" checked={online} onChange={(e) => toggleOnline(e.target.checked)} />
                        Les proposer aussi en vente en ligne (Flooz / T-Money sur la page Wi-Fi)
                    </label>
                    {!onlineSalesEnabled && online && (
                        <p className="empty-hint">La vente en ligne est actuellement désactivée pour ce routeur (onglet Réglages).</p>
                    )}
                    {error && <p className="error-text">{error}</p>}
                    <div className="hs-modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>Terminer</button>
                    </div>
                </>
            )}
        </Modal>
    );
}
