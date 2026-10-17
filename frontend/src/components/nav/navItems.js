import { LayoutDashboard, Radio, Wallet, Users, CreditCard, Ticket, UserCircle, Activity, Tag, Smartphone, Settings, HelpCircle, ShieldCheck } from 'lucide-react';

// Chaque page du menu, définie une seule fois. « hint » s'affiche sous le nom dans le panneau « Plus ».
const accueil = { to: '/tableau-de-bord', label: 'Accueil', icon: LayoutDashboard };
const tickets = { to: '/tickets', label: 'Tickets', icon: Ticket };
const argent = { to: '/wallet', label: 'Mon argent', icon: Wallet };
const clients = { to: '/tickets?vue=direct', label: 'Clients connectés', icon: Activity, hint: 'Qui utilise le Wi-Fi en ce moment' };
const routeurs = { to: '/routers', label: 'Mes routeurs', icon: Radio, hint: 'Ajouter, abonnement, état' };
const forfaits = { to: '/tickets?vue=forfaits', label: 'Forfaits et prix', icon: Tag, hint: 'Durées et prix des tickets' };
const pageWifi = { to: '/tickets?vue=wifi', label: 'Page Wi-Fi', icon: Smartphone, hint: 'Ce que voient vos clients' };
const reglages = { to: '/tickets?vue=reglages', label: 'Réglages du hotspot', icon: Settings };
const compte = { to: '/account', label: 'Mon compte', icon: UserCircle, hint: 'Nom, mot de passe, sécurité' };
const aide = { to: '/support', label: 'Aide', icon: HelpCircle };

// Menu latéral (ordinateur), du plus utilisé au plus rare.
export const sidebarGroups = [
    { title: null, items: [accueil] },
    { title: 'Au quotidien', items: [tickets, argent, clients] },
    { title: 'Mon installation', items: [routeurs, forfaits, pageWifi, reglages] },
];

// Barre du bas (téléphone), de part et d'autre du bouton central « Imprimer ».
export const bottomNavLeft = [accueil, tickets];
export const bottomNavRight = [{ ...argent, label: 'Argent' }];

// Panneau « Plus » (téléphone) : tout ce qui n'est pas dans la barre du bas.
export const moreGroups = [
    { title: 'Suivi', items: [clients] },
    { title: 'Mon installation', items: [routeurs, forfaits, pageWifi, reglages] },
    { title: 'Moi', items: [compte, aide] },
];

export const adminMoreItem = { to: '/admin', label: "Console d'administration", icon: ShieldCheck };

export const adminNavItems = [
    { to: '/admin', label: "Vue d'ensemble", icon: LayoutDashboard },
    { to: '/admin/users', label: 'Revendeurs', icon: Users },
    { to: '/admin/routers', label: 'Routeurs', icon: Radio },
    { to: '/admin/transactions', label: 'Transactions', icon: CreditCard },
];

// Un élément est actif quand l'adresse affichée correspond à sa page
// (et, pour la page Tickets, à sa vue : forfaits, page Wi-Fi, etc.).
export function isActive(to, location) {
    const [path, query = ''] = to.split('?');
    const current = location.pathname;
    const exact = path === '/tableau-de-bord' || path === '/admin';
    if (exact ? current !== path : current !== path && !current.startsWith(`${path}/`)) return false;
    if (path === '/tickets') {
        return new URLSearchParams(query).get('vue') === new URLSearchParams(location.search).get('vue');
    }
    return true;
}