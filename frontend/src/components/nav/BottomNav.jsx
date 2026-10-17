import { useCallback, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Printer, Menu } from 'lucide-react';
import { bottomNavLeft, bottomNavRight, moreGroups, adminMoreItem, isActive } from './navItems';
import MoreSheet from './MoreSheet';
import './BottomNav.css';

function NavItem({ to, label, icon: Icon, location }) {
    const active = isActive(to, location);
    return (
        <Link to={to} className={`bottom-nav-item${active ? ' active' : ''}`} aria-current={active ? 'page' : undefined}>
            <Icon size={20} strokeWidth={2} />
            <span className="bottom-nav-label">{label}</span>
        </Link>
    );
}

export default function BottomNav({ isAdmin, onLogout }) {
    const location = useLocation();
    // Le panneau « Plus » reste ouvert tant qu'on ne change pas de page :
    // il se referme tout seul après un clic sur un lien ou un retour arrière.
    const [openedOn, setOpenedOn] = useState(null);
    const moreOpen = openedOn !== null && openedOn === location.key;
    const closeMore = useCallback(() => setOpenedOn(null), []);

    const moreItems = moreGroups.flatMap((g) => g.items).concat(isAdmin ? [adminMoreItem] : []);
    const moreActive = moreItems.some((item) => isActive(item.to, location));

    return (
        <>
            <nav className="bottom-nav" aria-label="Menu principal">
                {bottomNavLeft.map((item) => <NavItem key={item.to} {...item} location={location} />)}

                <Link to="/tickets?action=creer" className="bottom-nav-item bottom-nav-print">
                    <span className="bottom-nav-print-btn" aria-hidden="true">
                        <Printer size={22} strokeWidth={2} />
                    </span>
                    <span className="bottom-nav-label">Imprimer</span>
                </Link>

                {bottomNavRight.map((item) => <NavItem key={item.to} {...item} location={location} />)}

                <button
                    type="button"
                    className={`bottom-nav-item${moreActive || moreOpen ? ' active' : ''}`}
                    onClick={() => setOpenedOn(location.key)}
                    aria-haspopup="dialog"
                    aria-expanded={moreOpen}
                >
                    <Menu size={20} strokeWidth={2} />
                    <span className="bottom-nav-label">Plus</span>
                </button>
            </nav>

            {moreOpen && <MoreSheet isAdmin={isAdmin} onClose={closeMore} onLogout={onLogout} />}
        </>
    );
}