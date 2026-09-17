import { NavLink } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { mainNavItems } from './navItems';
import './BottomNav.css';

export default function BottomNav({ isAdmin }) {
    const items = isAdmin
        ? [...mainNavItems, { to: '/admin', label: 'Admin', icon: ShieldCheck }]
        : mainNavItems;

    return (
        <nav className="bottom-nav">
            {items.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === '/'} className="bottom-nav-item">
                    <Icon size={20} strokeWidth={2} />
                    <span>{label}</span>
                </NavLink>
            ))}
        </nav>
    );
}