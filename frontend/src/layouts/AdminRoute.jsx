import { Navigate, Outlet, useOutletContext } from 'react-router-dom';

export default function AdminRoute() {
    const context = useOutletContext();
    if (!context.isAdmin) return <Navigate to="/tableau-de-bord" replace />;
    return <Outlet context={context} />;
}