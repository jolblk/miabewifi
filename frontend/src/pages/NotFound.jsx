import { Link } from 'react-router-dom';
import './Login.css';

export default function NotFound() {
    return (
        <div className="login-screen">
            <div className="login-box">
                <div className="login-logo">
                    <div className="login-logo-icon">M</div>
                    <span className="login-logo-name">MIABEWIFI</span>
                </div>

                <div className="login-brand">Page introuvable</div>
                <p className="login-sub">Cette page n'existe pas ou a été déplacée.</p>

                <p className="forgot-link" style={{ textAlign: 'center', marginTop: 16 }}>
                    <Link to="/">Retour à l'accueil</Link>
                </p>
            </div>
        </div>
    );
}
