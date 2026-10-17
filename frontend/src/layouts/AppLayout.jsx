import { useEffect, useRef } from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useViewport } from '../hooks/useViewport';
import { useAuth } from '../hooks/useAuth';
import BottomNav from '../components/nav/BottomNav';
import Sidebar from '../components/nav/Sidebar';
import NotificationsBell from '../components/NotificationsBell';
import SearchBar from '../components/SearchBar';
import { confirmDialog } from '../utils/confirm';
import './AppLayout.css';

export default function AppLayout() {
    const { isMobile } = useViewport();
    const { user, loading, isAdmin, logout } = useAuth();
    const { pathname } = useLocation();
    const mainRef = useRef(null);

    // Sur téléphone, c'est la zone centrale qui défile : on la remet en haut à chaque changement de page.
    useEffect(() => {
        mainRef.current?.scrollTo(0, 0);
    }, [pathname]);

    async function handleLogout() {
        const ok = await confirmDialog('Voulez-vous vraiment vous déconnecter ?', {
            confirmLabel: 'Se déconnecter',
            danger: true,
        });
        if (ok) logout();
    }

    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;

    if (isMobile) {
        return (
            <div className="mobile-shell">
                <header className="mobile-header">
                    <Link to="/tableau-de-bord" className="mobile-logo">
                        <span className="mobile-logo-dot" aria-hidden="true" />
                        MIABEWIFI
                    </Link>
                    <div className="mobile-header-actions">
                        <SearchBar />
                        <NotificationsBell />
                    </div>
                </header>
                <main className="mobile-main" ref={mainRef}>
                    <Outlet context={{ user, isAdmin, logout: handleLogout }} />
                </main>
                <BottomNav isAdmin={isAdmin} onLogout={handleLogout} />
            </div>
        );
    }

    return (
        <div style={{ display: 'flex' }}>
            <Sidebar user={user} isAdmin={isAdmin} onLogout={handleLogout} />
            <main style={{ flex: 1, padding: 24, minWidth: 0 }}>
                <div className="app-topbar">
                    <SearchBar />
                    <NotificationsBell />
                </div>
                <Outlet context={{ user, isAdmin, logout: handleLogout }} />
            </main>
        </div>
    );
}