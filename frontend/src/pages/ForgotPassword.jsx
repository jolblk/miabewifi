import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import './Login.css';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/auth/forgot-password', { email });
        } finally {
            setLoading(false);
            setSent(true);
        }
    }

    return (
        <div className="login-screen">
            <div className="login-box">
                <div className="login-logo">
                    <div className="login-logo-icon">M</div>
                    <span className="login-logo-name">MIABEWIFI</span>
                </div>

                <div className="login-brand">Mot de passe oublié</div>
                <p className="login-sub">Entrez votre email, nous vous enverrons un lien de réinitialisation.</p>

                {sent ? (
                    <p className="login-sub">
                        Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé. Vérifiez votre boîte mail.
                    </p>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div className="login-field">
                            <label htmlFor="email">Email</label>
                            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Votre email" />
                        </div>
                        <button type="submit" className="login-submit" disabled={loading}>
                            {loading ? 'Envoi...' : 'Envoyer le lien'}
                        </button>
                    </form>
                )}

                <p className="forgot-link" style={{ textAlign: 'center', marginTop: 16 }}>
                    <Link to="/login">Retour à la connexion</Link>
                </p>
            </div>
        </div>
    );
}