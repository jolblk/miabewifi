import { Link, useOutletContext } from 'react-router-dom';
import { LogOut, HelpCircle } from 'lucide-react';
import './Account.css';
import SecuritySettings from '../components/SecuritySettings';

// « Mon compte » : identité, sécurité et déconnexion. L'aide a sa propre page (« Aide »).
export default function Account() {
    const { user, logout } = useOutletContext();

    return (
        <div>
            <h1 className="page-title">Mon compte</h1>

            <div className="section-card router-meta" style={{ marginBottom: 16 }}>
                <span>Nom : <strong>{user?.nom}</strong></span>
                <span>Email : <strong>{user?.email}</strong></span>
            </div>

            <div className="section-card" style={{ marginBottom: 16 }}>
                <SecuritySettings />
            </div>

            <div className="account-actions">
                <Link to="/support" className="btn-secondary">
                    <HelpCircle size={16} /> Besoin d'aide ?
                </Link>
                <button type="button" className="btn-danger" onClick={logout}>
                    <LogOut size={16} /> Se déconnecter
                </button>
            </div>
        </div>
    );
}