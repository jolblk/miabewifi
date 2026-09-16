import { NavLink } from 'react-router-dom';
import { mainNavItems, adminNavItems } from './navItems';
import './Sidebar.css';

function NavGroup({ items }) {
    return items.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} end={to === '/'} className="sidebar-link">
            <Icon size={18} strokeWidth={2} />
            {label}
        </NavLink>
    ));
}

export default function Sidebar({ isAdmin }) {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">MIABEWIFI</div>
            <NavGroup items={mainNavItems} />
            {isAdmin && (
                <>
                    <div className="sidebar-section-title">Administration</div>
                    <NavGroup items={adminNavItems} />
                </>
            )}
        </aside>
    );
}