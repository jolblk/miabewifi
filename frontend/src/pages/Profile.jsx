import { useOutletContext } from 'react-router-dom';
import { LogOut } from 'lucide-react';

export default function Profile() {
    const { user, logout } = useOutletContext();

    return (
        <div>
            <h1 className="page-title">Profil</h1>

            <div className="section-card router-meta">
                <span>Nom : <strong>{user?.nom}</strong></span>
                <span>Email : <strong>{user?.email}</strong></span>
            </div>

            <button className="btn-danger" onClick={logout}>
                <LogOut size={16} /> Déconnexion
            </button>
        </div>
    );
}