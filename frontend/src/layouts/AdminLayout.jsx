import { NavLink, Outlet } from 'react-router-dom';
import '../pages/admin/Admin.css';

const adminTabs = [
    { to: '/admin', label: "Vue d'ensemble" },
    { to: '/admin/users', label: 'Utilisateurs' },
    { to: '/admin/routers', label: 'Routeurs' },
    { to: '/admin/transactions', label: 'Transactions' },
];

export default function AdminLayout() {
    return (
        <div>
            <div className="admin-tabs">
                {adminTabs.map(({ to, label }) => (
                    <NavLink key={to} to={to} end={to === '/admin'} className="admin-tab">
                        {label}
                    </NavLink>
                ))}
            </div>
            <Outlet />
        </div>
    );
}