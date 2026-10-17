import { Link, useLocation } from 'react-router-dom';
import { LogOut, Printer, HelpCircle } from 'lucide-react';
import { sidebarGroups, adminNavItems } from './navItems';
import './Sidebar.css';

// Un élément est actif quand l'adresse affichée correspond à sa page
// (et, pour la page Tickets, à sa vue : forfaits, page Wi-Fi, etc.).
function isActive(to, location) {
    const [path, query = ''] = to.split('?');
    const current = location.pathname;
    const exact = path === '/tableau-de-bord' || path === '/admin';
    if (exact ? current !== path : current !== path && !current.startsWith(`${path}/`)) return false;
    if (path === '/tickets') {
        return new URLSearchParams(query).get('vue') === new URLSearchParams(location.search).get('vue');
    }
    return true;
}

function SideLink({ to, label, icon: Icon, location }) {
    const active = isActive(to, location);
    return (
        <Link to={to} className={`sidebar-link${active ? ' active' : ''}`} aria-current={active ? 'page' : undefined}>
            <Icon size={18} strokeWidth={2} />
            <span>{label}</span>
        </Link>
    );
}

function initials(nom) {
    const letters = String(nom || '').trim().split(/\s+/).slice(0, 2).map((w) => w.charAt(0)).join('');
    return letters.toUpperCase() || '?';
}

export default function Sidebar({ user, isAdmin, onLogout }) {
    const location = useLocation();
    const onAccount = location.pathname === '/profile' || location.pathname === '/account';

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <span className="sidebar-logo-dot" aria-hidden="true" />
                MIABEWIFI
            </div>

            <Link to="/tickets?action=creer" className="sidebar-print">
                <Printer size={18} strokeWidth={2} />
                Imprimer des tickets
            </Link>

            <nav className="sidebar-nav" aria-label="Menu principal">
                {sidebarGroups.map((group, i) => (
                    <div key={group.title || i} className="sidebar-group">
                        {group.title && <div className="sidebar-section-title">{group.title}</div>}
                        {group.items.map((item) => (
                            <SideLink key={item.to} {...item} location={location} />
                        ))}
                    </div>
                ))}
                {isAdmin && (
                    <div className="sidebar-group">
                        <div className="sidebar-section-title">Administration</div>
                        {adminNavItems.map((item) => (
                            <SideLink key={item.to} {...item} location={location} />
                        ))}
                    </div>
                )}
            </nav>

            <div className="sidebar-bottom">
                <SideLink to="/support" label="Aide" icon={HelpCircle} location={location} />
                <div className="sidebar-user">
                    <Link to="/profile" className={`sidebar-user-link${onAccount ? ' active' : ''}`}>
                        <span className="sidebar-avatar" aria-hidden="true">{initials(user?.nom)}</span>
                        <span className="sidebar-user-text">
                            <strong>{user?.nom || 'Mon compte'}</strong>
                            <small>Mon compte</small>
                        </span>
                    </Link>
                    <button
                        type="button"
                        className="sidebar-logout"
                        onClick={onLogout}
                        title="Se déconnecter"
                        aria-label="Se déconnecter"
                    >
                        <LogOut size={18} strokeWidth={2} />
                    </button>
                </div>
            </div>
        </aside>
    );
}