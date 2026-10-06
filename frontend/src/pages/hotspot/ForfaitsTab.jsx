import { Pencil, Plus, Trash2 } from 'lucide-react';
import { formatAmount } from '../../utils/format';
import { formatQuota, humanDuration, speedLabel } from './hotspotUtils';

export default function ForfaitsTab({ profiles, forfaitSettings, busy, onNew, onEdit, onDelete }) {
    const items = profiles
        .map((p) => ({ profile: p, setting: forfaitSettings.find((s) => s.profile_name === p.name) }))
        .sort((a, b) => (a.setting?.prix ?? Infinity) - (b.setting?.prix ?? Infinity) || String(a.profile.name).localeCompare(String(b.profile.name)));

    return (
        <div>
            <div className="hs-tab-intro">
                <p className="empty-hint">Un forfait, c'est ce que vous vendez : une durée de connexion, une vitesse et un prix.</p>
                <button type="button" className="btn-primary" onClick={onNew}>
                    <Plus size={16} /> Nouveau forfait
                </button>
            </div>

            {items.length === 0 && (
                <div className="section-card"><p className="empty-hint">Aucun forfait sur ce routeur, ou le routeur ne répond pas.</p></div>
            )}

            <div className="hs-groups">
                {items.map(({ profile, setting }) => {
                    const shared = Number(profile['shared-users'] || 1);
                    const details = [
                        humanDuration(profile['session-timeout']) ? `${humanDuration(profile['session-timeout'])} de connexion` : 'durée non limitée',
                        speedLabel(profile['rate-limit']),
                        `${shared} appareil${shared > 1 ? 's' : ''}`,
                        setting?.validite_jours ? `valable ${setting.validite_jours} j` : null,
                        setting?.quota_mo ? `${formatQuota(setting.quota_mo)} de données` : null,
                    ].filter(Boolean).join(' · ');
                    return (
                        <div key={profile['.id'] || profile.name} className="section-card hs-forfait">
                            <div>
                                <strong>{humanDuration(profile['session-timeout']) || profile.name}</strong>
                                <div className="empty-hint hs-no-margin">{details}</div>
                                <div className="hs-tech-name">Nom sur le routeur : {profile.name}</div>
                            </div>
                            <div className="hs-group-actions">
                                {setting
                                    ? <span className="hs-price">{formatAmount(setting.prix)} F</span>
                                    : <span className="badge badge-warning">Prix à définir</span>}
                                <button type="button" className="btn-secondary hs-btn-sm" disabled={busy} onClick={() => onEdit(profile, setting)}>
                                    <Pencil size={14} /> Modifier
                                </button>
                                <button type="button" className="icon-btn" disabled={busy} onClick={() => onDelete(profile)} aria-label={`Supprimer le forfait ${profile.name}`}>
                                    <Trash2 size={15} />
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
