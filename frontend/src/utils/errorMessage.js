// Transforme une erreur axios en message lisible (en français) pour l'utilisateur.
export function getErrorMessage(err, fallback = 'Une erreur est survenue.') {
    if (!err?.response) {
        return 'Impossible de joindre le serveur. Vérifiez votre connexion.';
    }
    if (err.response.status === 429) {
        return 'Trop de tentatives. Réessayez dans une minute.';
    }
    const detail = err.response.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
        return 'Veuillez vérifier les informations saisies.';
    }
    return fallback;
}
