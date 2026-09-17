import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client';
import './Login.css';

export default function Register() {
    const [nom, setNom] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const navigate = useNavigate();

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');

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
            await api.post('/auth/register', { nom, email, password });
            setSuccess(true);
        } catch (err) {
            setError(err.response?.data?.detail || "Impossible de créer le compte.");
        } finally {
            setLoading(false);
        }
    }

    if (success) {
        return (
            <div className="login-screen">
                <div className="login-box">
                    <div className="login-brand">Compte créé</div>
                    <p className="login-sub">Vous pouvez maintenant vous connecter.</p>
                    <button className="login-submit" onClick={() => navigate('/login')}>
                        Aller à la connexion
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="login-screen">
            <form onSubmit={handleSubmit} className="login-box">
                <div className="login-logo">
                    <div className="login-logo-icon">M</div>
                    <span className="login-logo-name">MIABEWIFI</span>
                </div>

                <div className="login-brand">Créer un compte</div>
                <p className="login-sub">Gérez vos routeurs MikroTik en quelques clics.</p>

                {error && <div className="login-error">{error}</div>}

                <div className="login-field">
                    <label htmlFor="nom">Nom</label>
                    <input id="nom" type="text" required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Votre nom" />
                </div>

                <div className="login-field">
                    <label htmlFor="email">Email</label>
                    <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Votre email" />
                </div>

                <div className="login-field">
                    <label htmlFor="password">Mot de passe</label>
                    <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="8 caractères minimum" />
                </div>

                <div className="login-field">
                    <label htmlFor="confirm">Confirmer le mot de passe</label>
                    <input id="confirm" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Retapez le mot de passe" />
                </div>

                <button type="submit" className="login-submit" disabled={loading}>
                    {loading ? 'Création...' : 'Créer mon compte'}
                </button>

                <p className="forgot-link" style={{ textAlign: 'center', marginTop: 16 }}>
                    Déjà un compte ? <Link to="/login">Se connecter</Link>
                </p>
            </form>
        </div>
    );
}