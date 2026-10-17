import { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, LogOut } from 'lucide-react';
import { moreGroups, adminMoreItem, isActive } from './navItems';
import './MoreSheet.css';

// Panneau qui monte du bas de l'écran sur téléphone : réglages, compte, aide, déconnexion.
export default function MoreSheet({ isAdmin, onClose, onLogout }) {
    const location = useLocation();
    const sheetRef = useRef(null);

    // Échap ferme le panneau ; la page derrière ne défile pas tant qu'il est ouvert.
    useEffect(() => {
        function onKey(e) {
            if (e.key === 'Escape') onClose();
        }
        document.addEventListener('keydown', onKey);
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        sheetRef.current?.focus();
        return () => {
            document.removeEventListener('keydown', onKey);
            document.body.style.overflow = previousOverflow;
        };
    }, [onClose]);

    const groups = isAdmin
        ? [...moreGroups, { title: 'Administration', items: [adminMoreItem] }]
        : moreGroups;

    return (
        <div className="more-layer">
            <div className="more-backdrop" onClick={onClose} aria-hidden="true" />
            <div className="more-sheet" role="dialog" aria-modal="true" aria-label="Plus" tabIndex={-1} ref={sheetRef}>
                <div className="more-grab" aria-hidden="true" />

                {groups.map((group) => (
                    <section key={group.title} className="more-group">
                        <h2 className="more-group-title">{group.title}</h2>
                        <div className="more-list">
                            {group.items.map(({ to, label, hint, icon: Icon }) => {
                                const active = isActive(to, location);
                                return (
                                    <Link
                                        key={to}
                                        to={to}
                                        className={`more-item${active ? ' active' : ''}`}
                                        aria-current={active ? 'page' : undefined}
                                        onClick={onClose}
                                    >
                                        <span className="more-icon"><Icon size={18} strokeWidth={2} /></span>
                                        <span className="more-text">
                                            <strong>{label}</strong>
                                            {hint && <small>{hint}</small>}
                                        </span>
                                        <ChevronRight size={16} className="more-chevron" aria-hidden="true" />
                                    </Link>
                                );
                            })}
                        </div>
                    </section>
                ))}

                <button
                    type="button"
                    className="more-item more-logout"
                    onClick={() => { onClose(); onLogout(); }}
                >
                    <span className="more-icon"><LogOut size={18} strokeWidth={2} /></span>
                    <span className="more-text"><strong>Se déconnecter</strong></span>
                </button>
            </div>
        </div>
    );
}