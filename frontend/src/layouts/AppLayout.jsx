import { Outlet, Navigate } from 'react-router-dom';
import { useViewport } from '../hooks/useViewport';
import { useAuth } from '../hooks/useAuth';
import BottomNav from '../components/nav/BottomNav';
import Sidebar from '../components/nav/Sidebar';

export default function AppLayout() {
    const { isMobile } = useViewport();
    const { user, loading, isAdmin } = useAuth();

    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;

    if (isMobile) {
        return (
            <div>
                <main style={{ padding: '16px 16px calc(var(--bottomnav-height) + 16px)' }}>
                    <Outlet context={{ user, isAdmin }} />
                </main>
                <BottomNav />
            </div>
        );
    }

    return (
        <div style={{ display: 'flex' }}>
            <Sidebar isAdmin={isAdmin} />
            <main style={{ flex: 1, padding: 24 }}>
                <Outlet context={{ user, isAdmin }} />
            </main>
        </div>
    );
}