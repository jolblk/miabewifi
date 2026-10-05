// Formats d'affichage en français (dates, montants).
// Dates : toujours jj/mm/aaaa, quel que soit le navigateur de l'utilisateur.
// Montants : séparateur de milliers (15 000), espace insécable pour éviter les retours à la ligne.

export function formatDate(value) {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleDateString('fr-FR');
}

export function formatDateTime(value) {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export function formatAmount(value) {
    const n = Number(value);
    if (value === null || value === undefined || value === '' || !Number.isFinite(n)) {
        return String(value ?? '');
    }
    return n.toLocaleString('fr-FR').replace(/[\u202f\u00a0]/g, '\u00a0');
}
