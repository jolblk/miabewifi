import { Outlet, Navigate } from 'react-router-dom';
import { useViewport } from '../hooks/useViewport';
import { useAuth } from '../hooks/useAuth';
import BottomNav from '../components/nav/BottomNav';
import Sidebar from '../components/nav/Sidebar';
import NotificationsBell from '../components/NotificationsBell';
import SearchBar from '../components/SearchBar';

export default function AppLayout() {
    const { isMobile } = useViewport();
    const { user, loading, isAdmin, logout } = useAuth();

    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;

    if (isMobile) {
        return (
            <div>
                <main style={{ padding: '16px 16px calc(var(--bottomnav-height) + 16px)' }}>
                    <div className="app-topbar">
                        <SearchBar />
                        <NotificationsBell />
                    </div>
                    <Outlet context={{ user, isAdmin, logout }} />
                </main>
                <BottomNav isAdmin={isAdmin} />
            </div>
        );
    }

    return (
        <div style={{ display: 'flex' }}>
            <Sidebar isAdmin={isAdmin} onLogout={logout} />
            <main style={{ flex: 1, padding: 24 }}>
                <div className="app-topbar">
                    <SearchBar />
                    <NotificationsBell />
                </div>
                <Outlet context={{ user, isAdmin, logout }} />
            </main>
        </div>
    );
}