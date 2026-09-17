import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api/client';
import './Login.css';

export default function ResetPassword() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');
    const navigate = useNavigate();

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');

        if (!token) {
            setError('Lien invalide ou expiré.');
            return;
        }
        if (password.length < 8) {
            setError('Le mot de passe doit contenir au moins 8 caractères.');
            return;
        }
        if (password !== confirm) {
            setError('Les mots de passe ne correspondent pas.');
            return;
        }

        setLoading(true);
        try {
            await api.post('/auth/reset-password', { token, new_password: password });
            setSuccess(true);
        } catch (err) {
            setError(err.response?.data?.detail || "Impossible de réinitialiser le mot de passe.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="login-screen">
            <div className="login-box">
                <div className="login-logo">
                    <div className="login-logo-icon">M</div>
                    <span className="login-logo-name">MIABEWIFI</span>
                </div>

                <div className="login-brand">Nouveau mot de passe</div>

                {success ? (
                    <>
                        <p className="login-sub">Votre mot de passe a été réinitialisé avec succès.</p>
                        <button className="login-submit" onClick={() => navigate('/login')}>
                            Aller à la connexion
                        </button>
                    </>
                ) : (
                    <>
                        {!token && <div className="login-error">Lien invalide ou expiré.</div>}
                        {error && <div className="login-error">{error}</div>}

                        <form onSubmit={handleSubmit}>
                            <div className="login-field">
                                <label htmlFor="password">Nouveau mot de passe</label>
                                <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="8 caractères minimum" />
                            </div>
                            <div className="login-field">
                                <label htmlFor="confirm">Confirmer le mot de passe</label>
                                <input id="confirm" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Retapez le mot de passe" />
                            </div>
                            <button type="submit" className="login-submit" disabled={loading}>
                                {loading ? 'Réinitialisation...' : 'Réinitialiser'}
                            </button>
                        </form>
                    </>
                )}

                <p className="forgot-link" style={{ textAlign: 'center', marginTop: 16 }}>
                    <Link to="/login">Retour à la connexion</Link>
                </p>
            </div>
        </div>
    );
}