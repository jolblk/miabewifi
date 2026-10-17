import { LayoutDashboard, Radio, Wallet, Users, CreditCard, Ticket, UserCircle, Activity, Tag, Smartphone, Settings } from 'lucide-react';

// Menu latéral (ordinateur), du plus utilisé au plus rare.
// Les vues de la page Tickets se reconnaissent au paramètre « vue » de l'adresse.
export const sidebarGroups = [
    {
        title: null,
        items: [
            { to: '/tableau-de-bord', label: 'Accueil', icon: LayoutDashboard },
        ],
    },
    {
        title: 'Au quotidien',
        items: [
            { to: '/tickets', label: 'Tickets', icon: Ticket },
            { to: '/wallet', label: 'Mon argent', icon: Wallet },
            { to: '/tickets?vue=direct', label: 'Clients connectés', icon: Activity },
        ],
    },
    {
        title: 'Mon installation',
        items: [
            { to: '/routers', label: 'Mes routeurs', icon: Radio },
            { to: '/tickets?vue=forfaits', label: 'Forfaits et prix', icon: Tag },
            { to: '/tickets?vue=wifi', label: 'Page Wi-Fi', icon: Smartphone },
            { to: '/tickets?vue=reglages', label: 'Réglages du hotspot', icon: Settings },
        ],
    },
];

export const mobileNavItems = [
    { to: '/tableau-de-bord', label: 'Accueil', icon: LayoutDashboard },
    { to: '/routers', label: 'Routeurs', icon: Radio },
    { to: '/tickets', label: 'Tickets', icon: Ticket },
    { to: '/wallet', label: 'Portefeuille', icon: Wallet },
    { to: '/account', label: 'Mon compte', icon: UserCircle },
];

export const adminNavItems = [
    { to: '/admin', label: "Vue d'ensemble", icon: LayoutDashboard },
    { to: '/admin/users', label: 'Revendeurs', icon: Users },
    { to: '/admin/routers', label: 'Routeurs', icon: Radio },
    { to: '/admin/transactions', label: 'Transactions', icon: CreditCard },
];