import { LayoutDashboard, Radio, Wallet, Lock, HelpCircle, Users, CreditCard, Ticket, Activity, UserCircle } from 'lucide-react';

export const mainNavItems = [
    { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/routers', label: 'Routeurs', icon: Radio },
    { to: '/wallet', label: 'Portefeuille', icon: Wallet },
    { to: '/profile', label: 'Profil', icon: Lock },
    { to: '/support', label: 'Support', icon: HelpCircle },
    { to: '/hotspot', label: 'Tickets HotSpot', icon: Ticket },
    { to: '/hotspot/suivi', label: 'Suivi HotSpot', icon: Activity },
];

export const mobileNavItems = [
    { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/routers', label: 'Routeurs', icon: Radio },
    { to: '/wallet', label: 'Portefeuille', icon: Wallet },
    { to: '/account', label: 'Mon compte', icon: UserCircle },
    { to: '/hotspot', label: 'Tickets HotSpot', icon: Ticket },
    { to: '/hotspot/suivi', label: 'Suivi HotSpot', icon: Activity },
];

export const adminNavItems = [
    { to: '/admin', label: "Vue d'ensemble", icon: LayoutDashboard },
    { to: '/admin/users', label: 'Utilisateurs', icon: Users },
    { to: '/admin/routers', label: 'Tous les routeurs', icon: Radio },
    { to: '/admin/transactions', label: 'Transactions', icon: CreditCard },
];