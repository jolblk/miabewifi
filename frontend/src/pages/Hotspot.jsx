import { useState, useEffect } from 'react';
import { Plus, Ticket, Check, Download, RefreshCw, Trash2, X, Pencil } from 'lucide-react';
import { useHotspotData } from '../hooks/useHotspotData';
import { confirmDialog } from '../utils/confirm';
import './Hotspot.css';
import { formatAmount, formatDate } from '../utils/format';

// Un ticket peut cumuler plusieurs états : vendu, utilisé (le client s'est connecté), expiré.
function ticketBadges(v) {
    const sold = Boolean(v.sale);
    const used = Boolean(v.first_login_at);
    const expired = v.statut === 'EXPIRED';

    if (expired) {
        const badges = [{ label: 'Expiré', cls: 'badge-danger' }];
        if (sold) badges.unshift({ label: 'Vendu', cls: 'badge-warning' });
        return badges;
    }
    const badges = [];
    if (sold) badges.push({ label: 'Vendu', cls: 'badge-warning' });
    if (used) badges.push({ label: 'Utilisé', cls: 'badge-success' });
    if (badges.length === 0) badges.push({ label: 'Disponible', cls: 'badge-success' });
    return badges;
}

// Message d'erreur lisible : le serveur renvoie soit un texte, soit (erreur de saisie) une liste.
function errorMessage(err, fallback) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        return String(detail[0].msg || fallback).replace(/^Value error, /, '');
    }
    return fallback;
}

function formatQuota(quotaMo) {
    if (!quotaMo) return '';
    if (quotaMo < 1024) return `${quotaMo} Mo`;
    return `${(quotaMo / 1024).toFixed(1).replace(/\.0$/, '').replace('.', ',')} Go`;
}

// "24h" -> { valeur: '24', unite: 'h' } ; un format plus exotique (ex: "1d2h") est laissé vide.
function parseTimeout(value) {
    const m = /^(\d+)([hd])$/.exec(String(value || ''));
    return m ? { valeur: m[1], unite: m[2] } : { valeur: '', unite: 'h' };
}

const DEFAULT_BRAND_COLOR = '#7c3aed';

function batchSummary(batch) {
    let disponibles = 0;
    let vendus = 0;
    let expires = 0;
    batch.vouchers.forEach((v) => {
        if (v.statut === 'EXPIRED') expires += 1;
        else if (v.sale) vendus += 1;
        else disponibles += 1;
    });
    return `${disponibles} disponible(s) · ${vendus} vendu(s) · ${expires} expiré(s)`;
}

export default function Hotspot() {
    const {
        routers, selectedRouterId, setSelectedRouterId,
        batches, loading, error, profiles, currentRateLimit, settings,
        generateBatch, sellVoucher, syncNow, applyRateLimit, installLoginPage, downloadBatchPdf,
        deleteVoucher, deleteBatch, createProfile, deleteProfile,
        updateProfile, saveSettings, uploadLogo, removeLogo, setBatchOnlineSale,
        uploadBackground, removeBackground,
    } = useHotspotData();

    const [showForm, setShowForm] = useState(false);
    const [profileName, setProfileName] = useState('');
    const [prixUnitaire, setPrixUnitaire] = useState('');
    const [quantite, setQuantite] = useState('');
    const [validiteJours, setValiditeJours] = useState('30');
    const [busy, setBusy] = useState(false);
    const [actionError, setActionError] = useState('');
    const [actionInfo, setActionInfo] = useState('');
    const [rateLimit, setRateLimit] = useState('');

    const [showNewProfile, setShowNewProfile] = useState(false);
    const [newProfileName, setNewProfileName] = useState('');
    const [newProfileDureeValeur, setNewProfileDureeValeur] = useState('24');
    const [newProfileDureeUnite, setNewProfileDureeUnite] = useState('h');
    const [newProfilePartage, setNewProfilePartage] = useState('1');
    const [newProfileRate, setNewProfileRate] = useState('');

    const [quotaValeur, setQuotaValeur] = useState('');
    const [quotaUnite, setQuotaUnite] = useState('go');

    const [editingId, setEditingId] = useState(null);
    const [editDuree, setEditDuree] = useState('');
    const [editUnite, setEditUnite] = useState('h');
    const [editPartage, setEditPartage] = useState('1');
    const [editRate, setEditRate] = useState('');

    const [sOnline, setSOnline] = useState(true);
    const [sBrandName, setSBrandName] = useState('');
    const [sBrandColor, setSBrandColor] = useState('');
    const [sSlogan, setSSlogan] = useState('');
    const [sPhone, setSPhone] = useState('');
    const [sPrefix, setSPrefix] = useState('');
    const [sLength, setSLength] = useState('8');
    const [sDigits, setSDigits] = useState(false);

    useEffect(() => {
        setRateLimit(currentRateLimit);
    }, [currentRateLimit]);

    // Recopie les réglages du serveur dans le formulaire dès qu'ils changent
    // (chargement, changement de routeur, enregistrement).
    const [syncedSettings, setSyncedSettings] = useState(null);
    if (settings !== syncedSettings) {
        setSyncedSettings(settings);
        if (settings) {
            setSOnline(settings.online_sales_enabled);
            setSBrandName(settings.brand_name || '');
            setSBrandColor(settings.brand_color || '');
            setSSlogan(settings.brand_slogan || '');
            setSPhone(settings.brand_phone || '');
            setSPrefix(settings.code_prefix || '');
            setSLength(String(settings.code_length || 8));
            setSDigits(Boolean(settings.code_digits_only));
        }
    }

    async function handleGenerate(e) {
        e.preventDefault();
        if (!profileName.trim() || !prixUnitaire || !quantite) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const quotaMo = quotaValeur ? Math.round(Number(quotaValeur) * (quotaUnite === 'go' ? 1024 : 1)) : null;
            if (quotaValeur && !(quotaMo >= 1)) {
                setActionError('Quota de données invalide.');
                setBusy(false);
                return;
            }
            await generateBatch(profileName.trim(), Number(prixUnitaire), Number(quantite), validiteJours ? Number(validiteJours) : null, quotaMo);
            setProfileName('');
            setPrixUnitaire('');
            setQuantite('');
            setQuotaValeur('');
            setShowForm(false);
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la génération des tickets."));
        } finally {
            setBusy(false);
        }
    }

    async function handleSell(voucherId) {
        setBusy(true);
        setActionError('');
        try {
            await sellVoucher(voucherId);
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la vente du ticket."));
        } finally {
            setBusy(false);
        }
    }

    async function handleDeleteVoucher(voucherId) {
        if (!(await confirmDialog('Supprimer ce ticket ? Cette action est définitive.', { confirmLabel: 'Supprimer', danger: true }))) return;
        setBusy(true);
        setActionError('');
        try {
            await deleteVoucher(voucherId);
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la suppression du ticket."));
        } finally {
            setBusy(false);
        }
    }

    async function handleDeleteBatch(batchId) {
        if (!(await confirmDialog("Supprimer ce lot ? Les tickets déjà vendus seront conservés, les autres seront définitivement supprimés.", { confirmLabel: 'Supprimer', danger: true }))) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await deleteBatch(batchId);
            setActionInfo(
                res.supprimes > 0
                    ? `${res.supprimes} ticket(s) supprimé(s)${res.conserves_vendus ? `, ${res.conserves_vendus} conservé(s) (déjà vendus)` : ''}.`
                    : "Aucun ticket supprimé : tous ont déjà été vendus."
            );
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la suppression du lot."));
        } finally {
            setBusy(false);
        }
    }

    async function handleSync() {
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await syncNow();
            setActionInfo(`Mise à jour terminée : ${res.connexions_detectees} connexion(s) détectée(s), ${res.expires} ticket(s) expiré(s).`);
        } catch (err) {
            setActionError(errorMessage(err, "Impossible de mettre à jour les tickets."));
        } finally {
            setBusy(false);
        }
    }

    async function handleRateLimit(e) {
        e.preventDefault();
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await applyRateLimit(rateLimit.trim());
            setActionInfo(`Vitesse limitée à ${res.rate_limit} par client (${res.forfaits.join(', ')}).`);
        } catch (err) {
            const detail = err.response?.data?.detail;
            setActionError(typeof detail === 'string' ? detail : "Format invalide. Exemple : 2M/2M ou 512k/1M.");
        } finally {
            setBusy(false);
        }
    }

    async function handleCreateProfile(e) {
        e.preventDefault();
        if (!newProfileName.trim() || !newProfileDureeValeur) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const created = await createProfile(
                newProfileName.trim(),
                Number(newProfileDureeValeur),
                newProfileDureeUnite,
                Number(newProfilePartage) || 1,
                newProfileRate.trim() || null,
            );
            setProfileName(created.name);
            setNewProfileName('');
            setNewProfileDureeValeur('24');
            setNewProfilePartage('1');
            setNewProfileRate('');
            setShowNewProfile(false);
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la création du forfait."));
        } finally {
            setBusy(false);
        }
    }

    async function handleDeleteProfile(profile) {
        if (!(await confirmDialog(`Supprimer le forfait "${profile.name}" ? Les tickets déjà générés avec ce forfait continueront de fonctionner.`, { confirmLabel: 'Supprimer', danger: true }))) return;
        setBusy(true);
        setActionError('');
        try {
            await deleteProfile(profile['.id']);
            if (profileName === profile.name) setProfileName('');
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la suppression du forfait."));
        } finally {
            setBusy(false);
        }
    }

    function startEditProfile(profile) {
        const t = parseTimeout(profile['session-timeout']);
        setEditingId(profile['.id']);
        setEditDuree(t.valeur);
        setEditUnite(t.unite);
        setEditPartage(String(profile['shared-users'] || '1'));
        setEditRate(profile['rate-limit'] || '');
        setActionError('');
        setActionInfo('');
    }

    async function handleSaveProfile() {
        const changes = {};
        if (editDuree) {
            changes.duree_valeur = Number(editDuree);
            changes.duree_unite = editUnite;
        }
        if (editPartage) changes.partage = Number(editPartage);
        if (editRate.trim()) changes.rate_limit = editRate.trim();
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            await updateProfile(editingId, changes);
            setEditingId(null);
            setActionInfo("Forfait modifié. Les tickets déjà générés gardent leur durée d'origine ; les prochains lots utiliseront la nouvelle.");
        } catch (err) {
            setActionError(errorMessage(err, "Erreur lors de la modification du forfait."));
        } finally {
            setBusy(false);
        }
    }

    async function handleSaveSettings() {
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            await saveSettings({
                online_sales_enabled: sOnline,
                brand_name: sBrandName,
                brand_color: sBrandColor,
                brand_slogan: sSlogan,
                brand_phone: sPhone,
                code_prefix: sPrefix,
                code_length: Number(sLength) || 8,
                code_digits_only: sDigits,
            });
            setActionInfo("Réglages enregistrés. Pour changer la page de connexion du Wi-Fi, cliquez sur « Appliquer sur la page de connexion ».");
        } catch (err) {
            setActionError(errorMessage(err, "Impossible d'enregistrer les réglages."));
        } finally {
            setBusy(false);
        }
    }

    async function handleLogoChange(e) {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            await uploadLogo(file);
            setActionInfo("Logo enregistré. Cliquez sur « Appliquer sur la page de connexion » pour l'afficher sur le Wi-Fi.");
        } catch (err) {
            setActionError(errorMessage(err, "Impossible d'envoyer ce logo."));
        } finally {
            setBusy(false);
        }
    }

    async function handleBackgroundChange(e) {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            await uploadBackground(file);
            setActionInfo("Photo de fond enregistrée. Cliquez sur « Appliquer sur la page de connexion » pour l'afficher sur le Wi-Fi.");
        } catch (err) {
            setActionError(errorMessage(err, "Impossible d'envoyer cette photo."));
        } finally {
            setBusy(false);
        }
    }

    async function handleRemoveBackground() {
        setBusy(true);
        setActionError('');
        try {
            await removeBackground();
        } catch (err) {
            setActionError(errorMessage(err, "Impossible de retirer la photo de fond."));
        } finally {
            setBusy(false);
        }
    }

    async function handleRemoveLogo() {
        setBusy(true);
        setActionError('');
        try {
            await removeLogo();
        } catch (err) {
            setActionError(errorMessage(err, "Impossible de retirer le logo."));
        } finally {
            setBusy(false);
        }
    }

    async function handleToggleBatchOnline(batch) {
        setBusy(true);
        setActionError('');
        try {
            await setBatchOnlineSale(batch.id, !batch.online_sale);
        } catch (err) {
            setActionError(errorMessage(err, "Impossible de modifier ce lot."));
        } finally {
            setBusy(false);
        }
    }

    async function handleInstallLoginPage() {
        if (!(await confirmDialog("Installer les pages MIABEWIFI sur ce routeur (connexion avec vos tarifs, page après connexion, statut et déconnexion) ? Elles remplacent les pages actuelles de votre HotSpot.", { confirmLabel: 'Installer' }))) return;
        setBusy(true);
        setActionError('');
        setActionInfo('');
        try {
            const res = await installLoginPage();
            setActionInfo(res.message);
        } catch (err) {
            setActionError(errorMessage(err, "Impossible d'installer la page de connexion."));
        } finally {
            setBusy(false);
        }
    }

    return (
        <div>
            <div className="section-header" style={{ justifyContent: 'flex-end' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn-secondary" onClick={handleSync} disabled={!selectedRouterId || busy}>
                        <RefreshCw size={16} /> Actualiser
                    </button>
                    <button className="btn-primary" onClick={() => setShowForm((v) => !v)} disabled={!selectedRouterId}>
                        <Plus size={16} /> Générer des tickets
                    </button>
                </div>
            </div>

            {routers.length > 0 && (
                <div className="hotspot-router-picker">
                    <label className="field-label" htmlFor="routeur-select">Routeur</label>
                    <select
                        id="routeur-select"
                        className="text-input"
                        value={selectedRouterId || ''}
                        onChange={(e) => setSelectedRouterId(Number(e.target.value))}
                    >
                        {routers.map((r) => (
                            <option key={r.id} value={r.id}>{r.nom}</option>
                        ))}
                    </select>
                </div>
            )}

            {!loading && routers.length === 0 && (
                <div className="section-card">
                    <p className="empty-hint">Ajoutez d'abord un routeur pour pouvoir générer des tickets HotSpot.</p>
                </div>
            )}

            {actionError && <p className="error-text">{actionError}</p>}
            {actionInfo && <p className="success-text">{actionInfo}</p>}
            {error && <p className="error-text">{error}</p>}

            {selectedRouterId && (
                <form className="section-card" onSubmit={handleRateLimit}>
                    <h2>Réglages du HotSpot</h2>
                    <label className="field-label" htmlFor="rate-limit">
                        Appliquer la même vitesse à tous les forfaits (envoi/téléchargement)
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <input
                            id="rate-limit"
                            className="text-input"
                            style={{ maxWidth: 160 }}
                            value={rateLimit}
                            onChange={(e) => setRateLimit(e.target.value)}
                            placeholder="2M/2M"
                        />
                        <button className="btn-secondary" type="submit" disabled={busy || !rateLimit.trim()}>
                            Appliquer
                        </button>
                    </div>
                    <p className="empty-hint">
                        Évite qu'un seul client sature votre connexion. Exemples : 2M/2M, 1M/3M, 512k/1M.
                        Écrase la vitesse de tous les forfaits « Ticket-… ». Pour régler un seul forfait, utilisez le crayon dans la liste ci-dessous.
                    </p>
                    <button type="button" className="btn-secondary" disabled={busy} onClick={handleInstallLoginPage}>
                        Installer la page de connexion simplifiée
                    </button>
                    <p className="empty-hint">
                        Le client saisit un seul champ (le code) au lieu de deux. Installée automatiquement sur les
                        routeurs configurés par MIABEWIFI.
                    </p>

                    {profiles.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                            <label className="field-label">Forfaits existants</label>
                            <div className="voucher-grid">
                                {profiles.map((p) => (
                                    <div key={p['.id']} className="voucher-pill">
                                        <span>
                                            {p.name}{p['session-timeout'] ? ` — ${p['session-timeout']}` : ''}
                                            {p['rate-limit'] ? ` · ${p['rate-limit']}` : ''}
                                            {p['shared-users'] && p['shared-users'] !== '1' ? ` · ${p['shared-users']} appareils` : ''}
                                        </span>
                                        <button
                                            type="button"
                                            className="icon-btn"
                                            disabled={busy}
                                            aria-label={`Modifier ${p.name}`}
                                            onClick={() => startEditProfile(p)}
                                        >
                                            <Pencil size={14} />
                                        </button>
                                        <button
                                            type="button"
                                            className="icon-btn"
                                            disabled={busy}
                                            aria-label={`Supprimer ${p.name}`}
                                            onClick={() => handleDeleteProfile(p)}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>

                            {editingId && (
                                <div className="section-card" style={{ marginTop: '0.75rem' }}>
                                    <h2>Modifier le forfait {profiles.find((p) => p['.id'] === editingId)?.name}</h2>
                                    <label className="field-label" htmlFor="edit-duree">Durée de connexion cumulée</label>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <input
                                            id="edit-duree"
                                            type="number"
                                            min="1"
                                            max="999"
                                            className="text-input"
                                            style={{ maxWidth: 100 }}
                                            value={editDuree}
                                            onChange={(e) => setEditDuree(e.target.value)}
                                        />
                                        <select className="text-input" style={{ maxWidth: 140 }} value={editUnite} onChange={(e) => setEditUnite(e.target.value)}>
                                            <option value="h">Heures</option>
                                            <option value="d">Jours</option>
                                        </select>
                                    </div>
                                    <label className="field-label" htmlFor="edit-partage">Appareils simultanés autorisés</label>
                                    <input
                                        id="edit-partage"
                                        type="number"
                                        min="1"
                                        max="20"
                                        className="text-input"
                                        style={{ maxWidth: 100 }}
                                        value={editPartage}
                                        onChange={(e) => setEditPartage(e.target.value)}
                                    />
                                    <label className="field-label" htmlFor="edit-rate">Vitesse maximale par client</label>
                                    <input
                                        id="edit-rate"
                                        className="text-input"
                                        style={{ maxWidth: 160 }}
                                        value={editRate}
                                        onChange={(e) => setEditRate(e.target.value)}
                                        placeholder="2M/2M"
                                    />
                                    <p className="empty-hint">
                                        Les tickets déjà générés gardent leur durée d'origine ; seuls les prochains lots utilisent la nouvelle durée.
                                    </p>
                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        <button type="button" className="btn-primary" disabled={busy} onClick={handleSaveProfile}>Enregistrer</button>
                                        <button type="button" className="btn-secondary" disabled={busy} onClick={() => setEditingId(null)}>Annuler</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </form>
            )}

            {selectedRouterId && settings && (
                <div className="section-card">
                    <h2>Vente en ligne et personnalisation</h2>

                    <label className="hotspot-check">
                        <input type="checkbox" checked={sOnline} onChange={(e) => setSOnline(e.target.checked)} />
                        Vente en ligne activée (paiement Flooz / T-Money sur la page de connexion)
                    </label>
                    <p className="empty-hint">
                        Désactivée, plus personne ne peut payer en ligne ; vos tickets restent vendables à la main.
                        Vous choisissez aussi, lot par lot, ceux proposés en ligne (case « En ligne » sur chaque lot).
                    </p>

                    <label className="field-label" htmlFor="brand-name">Nom affiché sur la page de connexion et les tickets</label>
                    <input
                        id="brand-name"
                        className="text-input"
                        maxLength={40}
                        placeholder="ex : Cyber Chez Ama"
                        value={sBrandName}
                        onChange={(e) => setSBrandName(e.target.value)}
                    />

                    <label className="field-label" htmlFor="brand-slogan">Slogan sous le nom (facultatif)</label>
                    <input
                        id="brand-slogan"
                        className="text-input"
                        maxLength={60}
                        placeholder="ex : Internet rapide et abordable"
                        value={sSlogan}
                        onChange={(e) => setSSlogan(e.target.value)}
                    />

                    <label className="field-label" htmlFor="brand-phone">Téléphone d'aide affiché aux clients (facultatif)</label>
                    <input
                        id="brand-phone"
                        className="text-input"
                        type="tel"
                        maxLength={24}
                        placeholder="ex : 90 00 00 00"
                        value={sPhone}
                        onChange={(e) => setSPhone(e.target.value)}
                    />

                    <label className="field-label" htmlFor="brand-color">Couleur principale</label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <input
                            id="brand-color"
                            type="color"
                            value={sBrandColor || DEFAULT_BRAND_COLOR}
                            onChange={(e) => setSBrandColor(e.target.value)}
                        />
                        <span className="empty-hint">{sBrandColor || 'Couleur MIABEWIFI par défaut'}</span>
                        {sBrandColor && (
                            <button type="button" className="btn-secondary" onClick={() => setSBrandColor('')}>Couleur par défaut</button>
                        )}
                    </div>

                    <label className="field-label" htmlFor="brand-logo">Logo (PNG ou JPEG, 2 Mo maximum)</label>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        {settings.logo && <img className="hotspot-logo-preview" src={settings.logo} alt="Logo actuel" />}
                        <input id="brand-logo" type="file" accept="image/png,image/jpeg" disabled={busy} onChange={handleLogoChange} />
                        {settings.has_logo && (
                            <button type="button" className="btn-secondary" disabled={busy} onClick={handleRemoveLogo}>Retirer le logo</button>
                        )}
                    </div>

                    <label className="field-label" htmlFor="brand-background">Photo de fond de la page de connexion (JPEG ou PNG, 8 Mo maximum)</label>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        {settings.background_url && (
                            <img
                                src={settings.background_url}
                                alt="Photo de fond actuelle"
                                style={{ width: 120, height: 68, objectFit: 'cover', borderRadius: 8 }}
                            />
                        )}
                        <input id="brand-background" type="file" accept="image/png,image/jpeg" disabled={busy} onChange={handleBackgroundChange} />
                        {settings.has_background && (
                            <button type="button" className="btn-secondary" disabled={busy} onClick={handleRemoveBackground}>Retirer la photo</button>
                        )}
                    </div>
                    <p className="empty-hint">
                        Elle est automatiquement allégée pour s'afficher vite. Sans photo, le fond prend votre couleur principale.
                    </p>

                    <label className="field-label" htmlFor="code-prefix">Format des codes de tickets</label>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <input
                            id="code-prefix"
                            className="text-input"
                            style={{ maxWidth: 140 }}
                            maxLength={6}
                            placeholder="Préfixe (ex : WIFI)"
                            value={sPrefix}
                            onChange={(e) => setSPrefix(e.target.value.toUpperCase())}
                        />
                        <input
                            type="number"
                            min="6"
                            max="12"
                            className="text-input"
                            style={{ maxWidth: 110 }}
                            aria-label="Nombre de caractères après le préfixe"
                            value={sLength}
                            onChange={(e) => setSLength(e.target.value)}
                        />
                    </div>
                    <label className="hotspot-check">
                        <input type="checkbox" checked={sDigits} onChange={(e) => setSDigits(e.target.checked)} />
                        Codes composés uniquement de chiffres (8 chiffres minimum)
                    </label>
                    <p className="empty-hint">
                        Le préfixe (6 caractères max.) est suivi de 6 à 12 caractères au hasard. Ne s'applique qu'aux prochains lots.
                    </p>

                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button type="button" className="btn-primary" disabled={busy} onClick={handleSaveSettings}>Enregistrer</button>
                        <button type="button" className="btn-secondary" disabled={busy} onClick={handleInstallLoginPage}>
                            Appliquer sur la page de connexion
                        </button>
                    </div>
                    <p className="empty-hint">
                        Le nom, le slogan, le téléphone, la couleur, le logo et la photo s'affichent sur les pages du Wi-Fi une fois « Appliquer » cliqué (elles remplacent les pages actuelles du HotSpot). Le nom, la couleur et le logo figurent aussi sur les prochains PDF de tickets. une fois « Appliquer » cliqué (elle remplace la page actuelle du HotSpot), et sur les prochains PDF de tickets.
                    </p>
                </div>
            )}

            {showForm && (
                <form className="section-card" onSubmit={handleGenerate}>
                    <label className="field-label" htmlFor="profile-name">Forfait</label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <select
                            id="profile-name"
                            className="text-input"
                            value={profileName}
                            onChange={(e) => setProfileName(e.target.value)}
                        >
                            <option value="">Choisir un forfait…</option>
                            {profiles.map((p) => (
                                <option key={p.name} value={p.name}>
                                    {p.name}{p['session-timeout'] ? ` — ${p['session-timeout']} de connexion` : ''}
                                </option>
                            ))}
                        </select>
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => setShowNewProfile((v) => !v)}
                        >
                            {showNewProfile ? <X size={16} /> : <Plus size={16} />} Forfait
                        </button>
                    </div>

                    {showNewProfile && (
                        <div className="section-card" style={{ marginTop: '0.5rem' }}>
                            <label className="field-label" htmlFor="new-profile-name">Nom du nouveau forfait</label>
                            <input
                                id="new-profile-name"
                                className="text-input"
                                placeholder="ex : 12h, WeekEnd, Illimite-1j"
                                value={newProfileName}
                                onChange={(e) => setNewProfileName(e.target.value)}
                            />
                            <p className="empty-hint">Le préfixe « Ticket- » est ajouté automatiquement si absent.</p>

                            <label className="field-label" htmlFor="new-profile-duree">Durée de connexion cumulée</label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    id="new-profile-duree"
                                    type="number"
                                    min="1"
                                    max="999"
                                    className="text-input"
                                    style={{ maxWidth: 100 }}
                                    value={newProfileDureeValeur}
                                    onChange={(e) => setNewProfileDureeValeur(e.target.value)}
                                />
                                <select
                                    className="text-input"
                                    style={{ maxWidth: 140 }}
                                    value={newProfileDureeUnite}
                                    onChange={(e) => setNewProfileDureeUnite(e.target.value)}
                                >
                                    <option value="h">Heures</option>
                                    <option value="d">Jours</option>
                                </select>
                            </div>

                            <label className="field-label" htmlFor="new-profile-partage">Appareils simultanés autorisés</label>
                            <input
                                id="new-profile-partage"
                                type="number"
                                min="1"
                                max="20"
                                className="text-input"
                                style={{ maxWidth: 100 }}
                                value={newProfilePartage}
                                onChange={(e) => setNewProfilePartage(e.target.value)}
                            />

                            <label className="field-label" htmlFor="new-profile-rate">Vitesse maximale par client (vide = 2M/2M)</label>
                            <input
                                id="new-profile-rate"
                                className="text-input"
                                style={{ maxWidth: 160 }}
                                placeholder="2M/2M"
                                value={newProfileRate}
                                onChange={(e) => setNewProfileRate(e.target.value)}
                            />

                            <button
                                type="button"
                                className="btn-primary"
                                disabled={busy || !newProfileName.trim()}
                                onClick={handleCreateProfile}
                                style={{ marginTop: '0.5rem' }}
                            >
                                Créer ce forfait
                            </button>
                        </div>
                    )}
                    <label className="field-label" htmlFor="prix-unitaire">Prix unitaire (FCFA)</label>
                    <input
                        id="prix-unitaire"
                        type="number"
                        min="1"
                        value={prixUnitaire}
                        onChange={(e) => setPrixUnitaire(e.target.value)}
                        className="text-input"
                    />
                    <label className="field-label" htmlFor="quantite">Quantité</label>
                    <input
                        id="quantite"
                        type="number"
                        min="1"
                        max="500"
                        value={quantite}
                        onChange={(e) => setQuantite(e.target.value)}
                        className="text-input"
                    />
                    <label className="field-label" htmlFor="validite-jours">
                        Validité en jours après la 1re connexion (vide = sans limite)
                    </label>
                    <input
                        id="validite-jours"
                        type="number"
                        min="1"
                        max="365"
                        value={validiteJours}
                        onChange={(e) => setValiditeJours(e.target.value)}
                        className="text-input"
                    />
                    <label className="field-label" htmlFor="quota-valeur">
                        Quota de données par ticket (vide = illimité)
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                            id="quota-valeur"
                            type="number"
                            min="1"
                            className="text-input"
                            style={{ maxWidth: 120 }}
                            value={quotaValeur}
                            onChange={(e) => setQuotaValeur(e.target.value)}
                        />
                        <select className="text-input" style={{ maxWidth: 100 }} value={quotaUnite} onChange={(e) => setQuotaUnite(e.target.value)}>
                            <option value="mo">Mo</option>
                            <option value="go">Go</option>
                        </select>
                    </div>
                    <p className="empty-hint">
                        La durée du forfait est du temps de connexion cumulé (ex : 24 h = 24 heures réellement connectées).
                        La validité est un délai calendaire : passé ce délai, le ticket est supprimé même s'il lui reste du temps.
                    </p>
                    <button className="btn-primary" type="submit" disabled={busy}>
                        {busy ? 'Génération en cours...' : 'Générer'}
                    </button>
                </form>
            )}

            {loading && <p className="empty-hint">Chargement des tickets...</p>}

            {!loading && batches.length === 0 && routers.length > 0 && (
                <div className="section-card">
                    <p className="empty-hint">Aucun ticket généré pour ce routeur pour le moment.</p>
                </div>
            )}

            <div className="hotspot-batches">
                {batches.map((batch) => (
                    <div key={batch.id} className="section-card">
                        <div className="section-header">
                            <div>
                                <h2>{batch.profile_name} — {formatAmount(batch.prix_unitaire)} FCFA</h2>
                                <span className="empty-hint">
                                    {batchSummary(batch)}
                                    {batch.validite_jours ? ` · validité ${batch.validite_jours} j` : ''}
                                    {batch.quota_mo ? ` · quota ${formatQuota(batch.quota_mo)}` : ''}
                                </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span className="empty-hint">{formatDate(batch.created_at)}</span>
                                <label className="hotspot-check" title="Proposer ce lot sur la page de paiement en ligne">
                                    <input
                                        type="checkbox"
                                        checked={batch.online_sale !== false}
                                        disabled={busy}
                                        onChange={() => handleToggleBatchOnline(batch)}
                                    />
                                    En ligne
                                </label>
                                <button className="btn-secondary" onClick={() => downloadBatchPdf(batch.id)}>
                                    <Download size={14} /> PDF
                                </button>
                                <button className="btn-secondary router-menu-danger" disabled={busy} onClick={() => handleDeleteBatch(batch.id)}>
                                    <Trash2 size={14} /> Supprimer le lot
                                </button>
                            </div>
                        </div>
                        <div className="voucher-grid">
                            {batch.vouchers.map((v) => (
                                <div key={v.id} className="voucher-pill">
                                    <Ticket size={14} />
                                    <span>{v.code}</span>
                                    {ticketBadges(v).map((b) => (
                                        <span key={b.label} className={`badge ${b.cls}`}>{b.label}</span>
                                    ))}
                                    {v.statut === 'AVAILABLE' && (
                                        <button className="btn-secondary" disabled={busy} onClick={() => handleSell(v.id)}>
                                            <Check size={14} /> Vendre
                                        </button>
                                    )}
                                    {v.statut !== 'USED' && (
                                        <button className="icon-btn" disabled={busy} onClick={() => handleDeleteVoucher(v.id)} aria-label="Supprimer ce ticket">
                                            <Trash2 size={14} />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
