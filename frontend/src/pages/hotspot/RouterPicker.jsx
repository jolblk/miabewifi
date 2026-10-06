import { HEALTH_DOTS, routerHealth } from './hotspotUtils';
import { formatDate } from '../../utils/format';

const TITLES = {
    green: 'Tout est en ordre',
    orange: 'À surveiller',
    red: 'Routeur indisponible',
    grey: 'Vérification en cours…',
};

function subscriptionText(sub) {
    if (sub.kind === 'abonnement') return `Abonnement actif jusqu'au ${formatDate(sub.date)}`;
    if (sub.kind === 'essai') return `Essai gratuit jusqu'au ${formatDate(sub.date)}`;
    if (sub.kind === 'expire') return `Abonnement expiré depuis le ${formatDate(sub.date)}`;
    return 'Aucun abonnement';
}

// Choix du routeur, avec un point de couleur devant chaque nom, et le détail de l'état du routeur choisi.
export default function RouterPicker({ routers, selectedRouterId, onSelect, statuses, onGoToRouters }) {
    const selected = routers.find((r) => r.id === selectedRouterId);
    const health = selected ? routerHealth(selected, statuses[selected.id]) : null;

    return (
        <div className="hs-router">
            <label className="field-label" htmlFor="hs-router-select">Routeur</label>
            <select
                id="hs-router-select"
                className="text-input hs-router-select"
                value={selectedRouterId || ''}
                onChange={(e) => onSelect(Number(e.target.value))}
            >
                {routers.map((r) => (
                    <option key={r.id} value={r.id}>
                        {HEALTH_DOTS[routerHealth(r, statuses[r.id]).color]} {r.nom}
                    </option>
                ))}
            </select>

            {health && (
                <div className={`hs-router-state hs-state-${health.color}`}>
                    <span className="hs-dot" aria-hidden="true" />
                    <div className="hs-router-state-text">
                        <strong>{TITLES[health.color]}</strong>
                        <span>
                            {health.online === null ? 'Connexion au routeur…' : health.online ? 'En ligne' : 'Hors ligne'}
                            {' · '}
                            {subscriptionText(health.subscription)}
                        </span>
                        {health.online === false && (
                            <span className="hs-router-hint">
                                Le routeur ne répond pas : vérifiez qu'il est allumé et relié à Internet.
                                Les tickets déjà vendus continuent de fonctionner sur place.
                            </span>
                        )}
                        {!health.subscription.active && (
                            <span className="hs-router-hint">
                                Sans abonnement, vous ne pouvez plus créer de tickets ni vendre en ligne.{' '}
                                {onGoToRouters && (
                                    <button type="button" className="hs-link" onClick={onGoToRouters}>
                                        Activer un forfait
                                    </button>
                                )}
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
