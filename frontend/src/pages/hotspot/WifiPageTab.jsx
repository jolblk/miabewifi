import { useState } from 'react';
import { Upload, Wifi } from 'lucide-react';
import { DEFAULT_BRAND_COLOR, errorMessage, groupLabel } from './hotspotUtils';
import { formatAmount } from '../../utils/format';

// Aperçu de la page Wi-Fi, mis à jour en direct pendant la saisie.
function PhonePreview({ name, slogan, phone, color, logo, background, offers }) {
    return (
        <div className="hs-phone" style={{ '--hs-brand': color || DEFAULT_BRAND_COLOR }}>
            <div className="hs-phone-bg" style={background ? { backgroundImage: `url('${background}')` } : undefined} />
            <div className="hs-phone-veil" />
            <div className="hs-phone-content">
                {logo
                    ? <img className="hs-phone-logo" src={logo} alt="" />
                    : <div className="hs-phone-mark"><Wifi size={22} /></div>}
                <div className="hs-phone-name">{name || 'Connexion Wi-Fi'}</div>
                {slogan && <div className="hs-phone-slogan">{slogan}</div>}
                <div className="hs-phone-card">
                    <div className="hs-phone-input">CODE DU TICKET</div>
                    <div className="hs-phone-btn">Se connecter</div>
                </div>
                {offers.length > 0 && (
                    <>
                        <div className="hs-phone-label">Pas de ticket ? Achetez-le ici</div>
                        <div className="hs-phone-offers">
                            {offers.slice(0, 6).map((g) => (
                                <div key={g.key}><b>{groupLabel(g)}</b><span>{formatAmount(g.prix)} F</span></div>
                            ))}
                        </div>
                    </>
                )}
                {phone && <div className="hs-phone-contact">Besoin d'aide ? {phone}</div>}
            </div>
        </div>
    );
}

export default function WifiPageTab({
    settings, groups, busy, setBusy, onMessage,
    onSaveSettings, onInstall, onUploadLogo, onRemoveLogo, onUploadBackground, onRemoveBackground,
}) {
    const [name, setName] = useState(settings?.brand_name || '');
    const [slogan, setSlogan] = useState(settings?.brand_slogan || '');
    const [phone, setPhone] = useState(settings?.brand_phone || '');
    const [color, setColor] = useState(settings?.brand_color || '');

    const offers = settings?.online_sales_enabled ? groups.filter((g) => g.online && g.disponibles > 0) : [];

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

    function save(publish) {
        run(async () => {
            await onSaveSettings({ brand_name: name, brand_slogan: slogan, brand_phone: phone, brand_color: color });
            if (!publish) return 'Modifications enregistrées. Cliquez sur « Publier sur le Wi-Fi » pour les afficher aux clients.';
            await onInstall();
            return 'Page Wi-Fi publiée : vos clients voient maintenant la nouvelle version.';
        }, "Impossible d'enregistrer ou de publier la page Wi-Fi.");
    }

    function upload(e, action, fallback, info) {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        run(async () => { await action(file); return info; }, fallback);
    }

    return (
        <div className="hs-wifi">
            <div className="section-card">
                <label className="field-label" htmlFor="hs-w-name">Nom affiché</label>
                <input id="hs-w-name" className="text-input" maxLength={40} placeholder="ex : Cyber Chez Ama" value={name} onChange={(e) => setName(e.target.value)} />

                <label className="field-label hs-mt" htmlFor="hs-w-slogan">Slogan (facultatif)</label>
                <input id="hs-w-slogan" className="text-input" maxLength={60} placeholder="ex : Internet rapide et abordable" value={slogan} onChange={(e) => setSlogan(e.target.value)} />

                <label className="field-label hs-mt" htmlFor="hs-w-phone">Téléphone d'aide (facultatif)</label>
                <input id="hs-w-phone" className="text-input" type="tel" maxLength={24} placeholder="ex : 90 00 00 00" value={phone} onChange={(e) => setPhone(e.target.value)} />

                <label className="field-label hs-mt" htmlFor="hs-w-color">Couleur principale</label>
                <div className="hs-inline">
                    <input id="hs-w-color" type="color" value={color || DEFAULT_BRAND_COLOR} onChange={(e) => setColor(e.target.value)} />
                    <span className="empty-hint hs-no-margin">{color || 'Couleur MIABEWIFI par défaut'}</span>
                    {color && <button type="button" className="hs-link" onClick={() => setColor('')}>Couleur par défaut</button>}
                </div>

                <span className="field-label hs-mt">Logo (PNG ou JPEG)</span>
                <div className="hs-inline">
                    {settings?.logo && <img className="hs-thumb" src={settings.logo} alt="Logo actuel" />}
                    <label className="btn-secondary hs-btn-sm hs-file">
                        <Upload size={14} /> {settings?.has_logo ? 'Changer' : 'Ajouter un logo'}
                        <input type="file" accept="image/png,image/jpeg" disabled={busy}
                            onChange={(e) => upload(e, onUploadLogo, "Impossible d'envoyer ce logo.", 'Logo enregistré. Publiez la page pour l\'afficher sur le Wi-Fi.')} />
                    </label>
                    {settings?.has_logo && (
                        <button type="button" className="hs-link" disabled={busy} onClick={() => run(async () => { await onRemoveLogo(); }, 'Impossible de retirer le logo.')}>Retirer</button>
                    )}
                </div>

                <span className="field-label hs-mt">Photo de fond (JPEG ou PNG)</span>
                <div className="hs-inline">
                    {settings?.background_url && <img className="hs-thumb hs-thumb-wide" src={settings.background_url} alt="Photo de fond actuelle" />}
                    <label className="btn-secondary hs-btn-sm hs-file">
                        <Upload size={14} /> {settings?.has_background ? 'Changer' : 'Ajouter une photo'}
                        <input type="file" accept="image/png,image/jpeg" disabled={busy}
                            onChange={(e) => upload(e, onUploadBackground, "Impossible d'envoyer cette photo.", 'Photo enregistrée. Publiez la page pour l\'afficher sur le Wi-Fi.')} />
                    </label>
                    {settings?.has_background && (
                        <button type="button" className="hs-link" disabled={busy} onClick={() => run(async () => { await onRemoveBackground(); }, 'Impossible de retirer la photo.')}>Retirer</button>
                    )}
                </div>
                <p className="empty-hint">La photo est allégée automatiquement. Sans photo, le fond prend votre couleur.</p>

                <div className="hs-inline hs-mt">
                    <button type="button" className="btn-primary" disabled={busy} onClick={() => save(true)}>
                        <Wifi size={16} /> Publier sur le Wi-Fi
                    </button>
                    <button type="button" className="btn-secondary" disabled={busy} onClick={() => save(false)}>Enregistrer sans publier</button>
                </div>
                <p className="empty-hint hs-mt">
                    « Publier » installe vos pages sur le routeur (connexion, page après connexion, temps restant, déconnexion).
                    Elles remplacent les pages actuelles du HotSpot.
                </p>
            </div>

            <div className="hs-wifi-preview">
                <span className="field-label">Aperçu</span>
                <PhonePreview
                    name={name}
                    slogan={slogan}
                    phone={phone}
                    color={color}
                    logo={settings?.logo}
                    background={settings?.background_url}
                    offers={offers}
                />
            </div>
        </div>
    );
}
