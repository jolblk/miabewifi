// Outils partagés par la page « Tickets hotspots » : libellés en français simple,
// regroupement des tickets par forfait, état des routeurs.

export const DEFAULT_BRAND_COLOR = '#7c3aed';

// Vitesses proposées, au lieu du format technique RouterOS (« 2M/2M »).
export const SPEEDS = [
    { value: '1M/1M', label: 'Lente', hint: '1 Mb/s' },
    { value: '2M/2M', label: 'Normale', hint: '2 Mb/s' },
    { value: '5M/5M', label: 'Rapide', hint: '5 Mb/s' },
    { value: '10M/10M', label: 'Très rapide', hint: '10 Mb/s' },
];

export function speedLabel(rate) {
    if (!rate) return 'vitesse illimitée';
    const known = SPEEDS.find((s) => s.value.toLowerCase() === String(rate).toLowerCase());
    return known ? `vitesse ${known.label.toLowerCase()}` : `vitesse ${rate}`;
}

// Durée RouterOS (« 1h », « 1d », « 1w », « 1d02:00:00 », « 30m ») -> secondes.
export function durationSeconds(value) {
    const text = String(value || '').trim();
    if (!text) return 0;
    let total = 0;
    const units = { w: 604800, d: 86400, h: 3600, m: 60, s: 1 };
    const re = /(\d+)([wdhms])/g;
    let m;
    let rest = text;
    while ((m = re.exec(text)) !== null) {
        total += Number(m[1]) * units[m[2]];
    }
    rest = text.replace(/(\d+)([wdhms])/g, '');
    const clock = /(\d+):(\d{2}):(\d{2})/.exec(rest);
    if (clock) total += Number(clock[1]) * 3600 + Number(clock[2]) * 60 + Number(clock[3]);
    return total;
}

export function humanDuration(value) {
    const secs = durationSeconds(value);
    if (!secs) return '';
    if (secs % 86400 === 0) {
        const days = secs / 86400;
        return days === 1 ? '24 heures' : `${days} jours`;
    }
    if (secs % 3600 === 0) {
        const hours = secs / 3600;
        return hours === 1 ? '1 heure' : `${hours} heures`;
    }
    const minutes = Math.round(secs / 60);
    return `${minutes} minutes`;
}

// Pour le formulaire : « 7d » -> { valeur: '7', unite: 'd' } ; « 3h » -> { valeur: '3', unite: 'h' }.
export function durationParts(value) {
    const secs = durationSeconds(value);
    if (!secs) return { valeur: '', unite: 'h' };
    if (secs % 86400 === 0) return { valeur: String(secs / 86400), unite: 'd' };
    return { valeur: String(Math.max(1, Math.round(secs / 3600))), unite: 'h' };
}

export function formatQuota(quotaMo) {
    if (!quotaMo) return '';
    if (quotaMo < 1024) return `${quotaMo} Mo`;
    return `${(quotaMo / 1024).toFixed(1).replace(/\.0$/, '').replace('.', ',')} Go`;
}

// Nom lisible d'un forfait : sa durée réelle (« 1 heure ») plutôt que son nom technique.
export function forfaitTitle(profileName, profiles, limitUptime) {
    const profile = (profiles || []).find((p) => p.name === profileName);
    return humanDuration(profile?.['session-timeout']) || humanDuration(limitUptime) || profileName;
}

// Forfaits proposés à l'utilisateur : tous, sauf « default », le forfait interne de MikroTik.
export function sellableProfiles(profiles) {
    return (profiles || []).filter((p) => p.name && p.name !== 'default');
}

export function isAvailable(v) {
    return v.statut === 'AVAILABLE' && !v.sale;
}

// Un ticket peut cumuler plusieurs états : vendu, utilisé (le client s'est connecté), expiré.
export function ticketBadges(v) {
    const sold = Boolean(v.sale);
    const used = Boolean(v.first_login_at);
    if (v.statut === 'EXPIRED') {
        return sold ? [{ label: 'Vendu', cls: 'badge-warning' }, { label: 'Expiré', cls: 'badge-danger' }] : [{ label: 'Expiré', cls: 'badge-danger' }];
    }
    const badges = [];
    if (sold) badges.push({ label: 'Vendu', cls: 'badge-warning' });
    if (used) badges.push({ label: 'Utilisé', cls: 'badge-success' });
    if (badges.length === 0) badges.push({ label: 'Disponible', cls: 'badge-success' });
    return badges;
}

// Regroupe les lots par forfait vendu (même forfait, même prix, mêmes options).
export function groupBatches(batches, profiles) {
    const groups = new Map();
    const sorted = [...(batches || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    sorted.forEach((batch) => {
        const key = [batch.profile_name, batch.prix_unitaire, batch.validite_jours || '', batch.quota_mo || ''].join('|');
        if (!groups.has(key)) {
            groups.set(key, {
                key,
                profile_name: batch.profile_name,
                prix: batch.prix_unitaire,
                validite_jours: batch.validite_jours,
                quota_mo: batch.quota_mo,
                title: forfaitTitle(batch.profile_name, profiles, batch.limit_uptime),
                batches: [],
                total: 0,
                disponibles: 0,
                vendus: 0,
                expires: 0,
                online: false,
                nextVoucher: null,
                lastCreatedAt: batch.created_at,
            });
        }
        const g = groups.get(key);
        g.batches.push(batch);
        g.lastCreatedAt = batch.created_at;
        if (batch.online_sale !== false) g.online = true;
        (batch.vouchers || []).forEach((v) => {
            g.total += 1;
            if (v.statut === 'EXPIRED') g.expires += 1;
            else if (v.sale) g.vendus += 1;
            if (isAvailable(v)) {
                g.disponibles += 1;
                if (!g.nextVoucher) g.nextVoucher = v;
            }
        });
    });
    return [...groups.values()].sort((a, b) => a.prix - b.prix);
}

export function isLowStock(group) {
    return group.disponibles > 0 && group.disponibles <= Math.max(5, Math.ceil(group.total * 0.1));
}

export function groupLabel(group) {
    return `${group.title}${group.quota_mo ? ` · ${formatQuota(group.quota_mo)}` : ''}`;
}

// État d'un routeur pour le sélecteur : vert (en ligne + abonnement), orange (un des deux manque),
// rouge (hors ligne et sans abonnement), gris (vérification en cours).
export const HEALTH_DOTS = { green: '🟢', orange: '🟠', red: '🔴', grey: '⚪' };

export function routerHealth(router, status) {
    const now = new Date();
    const sub = router.subscription_expires_at ? new Date(router.subscription_expires_at) : null;
    const trial = router.trial_expires_at ? new Date(router.trial_expires_at) : null;
    let subscription;
    if (sub && sub > now) subscription = { kind: 'abonnement', active: true, date: sub };
    else if (trial && trial > now) subscription = { kind: 'essai', active: true, date: trial };
    else if (sub || trial) subscription = { kind: 'expire', active: false, date: sub || trial };
    else subscription = { kind: 'aucun', active: false, date: null };

    if (status === undefined) return { color: 'grey', online: null, subscription };
    const online = status === null ? Boolean(router.is_connected) : Boolean(status.connecte);
    const color = online && subscription.active ? 'green' : online || subscription.active ? 'orange' : 'red';
    return { color, online, subscription };
}

// Message d'erreur lisible : le serveur renvoie soit un texte, soit (erreur de saisie) une liste.
export function errorMessage(err, fallback) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        return String(detail[0].msg || fallback).replace(/^Value error, /, '');
    }
    return fallback;
}

export function isSameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
