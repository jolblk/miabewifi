import { NavLink } from 'react-router-dom';
import { mainNavItems } from './navItems';
import './BottomNav.css';

export default function BottomNav() {
    return (
        <nav className="bottom-nav">
            {mainNavItems.slice(0, 5).map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === '/'} className="bottom-nav-item">
                    <Icon size={20} strokeWidth={2} />
                    <span>{label}</span>
                </NavLink>
            ))}
        </nav>
    );
}