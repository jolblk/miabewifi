import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { SPEEDS, errorMessage } from './hotspotUtils';

export default function SettingsTab({ settings, currentRateLimit, busy, setBusy, onMessage, onSaveSettings, onApplyRate, onSync }) {
    const [rate, setRate] = useState(currentRateLimit || '2M/2M');
    const [prefix, setPrefix] = useState(settings?.code_prefix || '');
    const [length, setLength] = useState(String(settings?.code_length || 8));
    const [digits, setDigits] = useState(Boolean(settings?.code_digits_only));
    const knownRate = SPEEDS.some((s) => s.value.toLowerCase() === String(currentRateLimit || '').toLowerCase());

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

    const example = `${prefix}${'K7QM4XPA2R9TWE'.slice(0, Number(length) || 8)}`;
    const exampleDigits = `${prefix}${'48210735961284'.slice(0, Number(length) || 8)}`;

    return (
        <div className="section-card hs-settings">
            <div className="hs-setting">
                <div>
                    <strong>Vente en ligne</strong>
                    <span className="empty-hint hs-no-margin">Les clients paient par Flooz ou T-Money directement sur la page Wi-Fi.</span>
                </div>
                <label className="hs-toggle-line hs-toggle-inline">
                    <input
                        type="checkbox"
                        checked={Boolean(settings?.online_sales_enabled)}
                        disabled={busy}
                        onChange={(e) => run(async () => {
                            await onSaveSettings({ online_sales_enabled: e.target.checked });
                            return e.target.checked ? 'Vente en ligne activée.' : 'Vente en ligne désactivée : vos tickets restent vendables au comptoir.';
                        }, 'Impossible de modifier la vente en ligne.')}
                    />
                    {settings?.online_sales_enabled ? 'Activée' : 'Désactivée'}
                </label>
            </div>

            <div className="hs-setting">
                <div>
                    <strong>Vitesse de tous les forfaits « Ticket »</strong>
                    <span className="empty-hint hs-no-margin">Vitesse maximale par client, appliquée d'un coup à tous les forfaits dont le nom commence par « Ticket ».</span>
                </div>
                <div className="hs-inline">
                    <select className="text-input hs-input-small" value={rate} onChange={(e) => setRate(e.target.value)}>
                        {SPEEDS.map((s) => <option key={s.value} value={s.value}>{s.label} ({s.hint})</option>)}
                        {currentRateLimit && !knownRate && <option value={currentRateLimit}>Personnalisée ({currentRateLimit})</option>}
                    </select>
                    <button type="button" className="btn-secondary hs-btn-sm" disabled={busy}
                        onClick={() => run(async () => {
                            const res = await onApplyRate(rate);
                            return `Vitesse appliquée à ${res.forfaits.length} forfait(s).`;
                        }, 'Impossible de modifier la vitesse.')}>
                        Appliquer
                    </button>
                </div>
            </div>

            <div className="hs-setting hs-setting-col">
                <div>
                    <strong>Format des codes</strong>
                    <span className="empty-hint hs-no-margin">
                        Exemple de code : <span className="mono">{digits ? exampleDigits : example}</span>. Ne s'applique qu'aux prochains tickets.
                    </span>
                </div>
                <div className="hs-inline">
                    <input className="text-input hs-input-small" maxLength={6} placeholder="Préfixe (ex : WIFI)" value={prefix} onChange={(e) => setPrefix(e.target.value.toUpperCase())} aria-label="Préfixe des codes" />
                    <select className="text-input hs-input-small" value={length} onChange={(e) => setLength(e.target.value)} aria-label="Nombre de caractères">
                        {[6, 7, 8, 9, 10, 11, 12].map((n) => <option key={n} value={n}>{n} caractères</option>)}
                    </select>
                    <label className="hs-toggle-line hs-toggle-inline">
                        <input type="checkbox" checked={digits} onChange={(e) => setDigits(e.target.checked)} />
                        Chiffres uniquement
                    </label>
                    <button type="button" className="btn-secondary hs-btn-sm" disabled={busy}
                        onClick={() => run(async () => {
                            await onSaveSettings({ code_prefix: prefix, code_length: Number(length), code_digits_only: digits });
                            return 'Format des codes enregistré.';
                        }, "Impossible d'enregistrer le format des codes.")}>
                        Enregistrer
                    </button>
                </div>
            </div>

            <div className="hs-setting">
                <div>
                    <strong>Synchronisation avec le routeur</strong>
                    <span className="empty-hint hs-no-margin">Se fait toute seule régulièrement. Forcez-la si un ticket semble mal indiqué.</span>
                </div>
                <button type="button" className="btn-secondary hs-btn-sm" disabled={busy}
                    onClick={() => run(async () => {
                        const res = await onSync();
                        return `Mise à jour terminée : ${res.connexions_detectees} connexion(s) détectée(s), ${res.expires} ticket(s) expiré(s).`;
                    }, 'Impossible de joindre le routeur.')}>
                    <RefreshCw size={14} /> Actualiser maintenant
                </button>
            </div>
        </div>
    );
}
