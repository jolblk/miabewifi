import { useEffect, useState } from 'react';
import { Printer } from 'lucide-react';
import api from '../../api/client';
import { durationSeconds, humanDuration, sellableProfiles } from '../hotspot/hotspotUtils';
import { getErrorMessage } from '../../utils/errorMessage';

// Prix proposés au démarrage, d'après la durée du forfait. Le revendeur peut les changer ici
// ou plus tard dans « Forfaits et prix ».
function suggestedPrice(seconds) {
    if (!seconds) return '';
    if (seconds <= 3600) return 100;
    if (seconds <= 3 * 3600) return 200;
    if (seconds <= 86400) return 500;
    if (seconds <= 7 * 86400) return 2500;
    return '';
}

// Fin de l'installation : les forfaits créés sur le routeur, avec un prix déjà proposé.
// Un bouton enregistre les prix puis ouvre l'impression des premiers tickets.
export default function FirstPrices({ routerId, onDone }) {
    const [rows, setRows] = useState(null);        // null = chargement
    const [loadError, setLoadError] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    function fetchRows() {
        Promise.all([
            api.get(`/hotspot/${routerId}/profiles`),
            api.get(`/hotspot/${routerId}/forfait-settings`),
        ])
            .then(([profilesRes, settingsRes]) => {
                const settings = settingsRes.data || [];
                const list = sellableProfiles(profilesRes.data)
                    .map((p) => {
                        const seconds = durationSeconds(p['session-timeout']);
                        const saved = settings.find((s) => s.profile_name === p.name);
                        return {
                            name: p.name,
                            label: humanDuration(p['session-timeout']) || p.name,
                            seconds,
                            prix: String(saved ? saved.prix : suggestedPrice(seconds)),
                            validite_jours: saved?.validite_jours ?? null,
                            quota_mo: saved?.quota_mo ?? null,
                        };
                    })
                    .sort((a, b) => (a.seconds || Infinity) - (b.seconds || Infinity));
                setRows(list);
            })
            .catch((err) => setLoadError(getErrorMessage(err, 'Impossible de lire les forfaits du routeur.')));
    }

    useEffect(() => {
        fetchRows();
    }, [routerId]); // eslint-disable-line react-hooks/exhaustive-deps

    function retry() {
        setLoadError('');
        setRows(null);
        fetchRows();
    }

    function setPrix(name, value) {
        setRows((prev) => prev.map((r) => (r.name === name ? { ...r, prix: value } : r)));
    }

    async function handleSave() {
        const filled = rows.filter((r) => String(r.prix).trim() !== '');
        if (filled.length === 0) {
            setError('Indiquez au moins un prix.');
            return;
        }
        if (filled.some((r) => !Number.isInteger(Number(r.prix)) || Number(r.prix) <= 0)) {
            setError('Les prix sont des nombres entiers en FCFA (ex. 500).');
            return;
        }
        setBusy(true);
        setError('');
        try {
            for (const r of filled) {
                await api.put(`/hotspot/${routerId}/forfait-settings/${encodeURIComponent(r.name)}`, {
                    prix: Number(r.prix),
                    validite_jours: r.validite_jours,
                    quota_mo: r.quota_mo,
                });
            }
            onDone(`/tickets?action=creer&routeur=${routerId}`);
        } catch (err) {
            setError(getErrorMessage(err, "Impossible d'enregistrer les prix. Réessayez."));
            setBusy(false);
        }
    }

    if (loadError) {
        return (
            <div className="wizard-prices">
                <p className="error-text">{loadError}</p>
                <button type="button" className="btn-secondary wizard-copy-btn" onClick={retry}>Réessayer</button>
            </div>
        );
    }

    if (rows === null) {
        return <p className="wizard-hint">Lecture des forfaits du routeur…</p>;
    }

    if (rows.length === 0) {
        return (
            <p className="wizard-hint">
                Aucun forfait sur ce routeur pour le moment : vous pourrez en créer dans « Forfaits et prix ».
            </p>
        );
    }

    return (
        <div className="wizard-prices">
            <h2>Vos prix</h2>
            <p className="wizard-hint">Proposés pour démarrer : changez-les si besoin, ils seront utilisés pour l'impression et la vente en ligne.</p>
            <div className="wizard-price-list">
                {rows.map((r) => (
                    <label key={r.name} className="wizard-price-row" htmlFor={`prix-${r.name}`}>
                        <span>{r.label}</span>
                        <span className="wizard-price-input">
                            <input
                                id={`prix-${r.name}`}
                                className="text-input"
                                type="number"
                                inputMode="numeric"
                                min="1"
                                step="1"
                                value={r.prix}
                                onChange={(e) => setPrix(r.name, e.target.value)}
                            />
                            F
                        </span>
                    </label>
                ))}
            </div>
            {error && <p className="error-text">{error}</p>}
            <button type="button" className="btn-primary wizard-prices-cta" disabled={busy} onClick={handleSave}>
                <Printer size={18} /> {busy ? 'Enregistrement…' : 'Imprimer mes premiers tickets'}
            </button>
        </div>
    );
}