import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import api from '../api/client';
import './Login.css';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [remember, setRemember] = useState(true);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const body = new URLSearchParams();
            body.set('username', email);
            body.set('password', password);
            const res = await api.post('/auth/login', body, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            });
            const storage = remember ? localStorage : sessionStorage;
            storage.setItem('miabewifi_token', res.data.access_token);
            navigate('/', { replace: true });
        } catch (err) {
            setError(err.response?.data?.detail || 'Connexion impossible.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="login-screen">
            <form onSubmit={handleSubmit} className="login-box">
                <div className="login-logo">
                    <div className="login-logo-icon">M</div>
                    <span className="login-logo-name">MIABEWIFI</span>
                </div>

                <div className="login-brand">Bon retour</div>
                <p className="login-sub">Pilotez vos routeurs MikroTik depuis n'importe où.</p>

                {error && <div className="login-error">{error}</div>}

                <div className="login-field">
                    <label htmlFor="email">Email</label>
                    <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Votre email" />
                </div>

                <div className="login-field">
                    <label htmlFor="password">Mot de passe</label>
                    <div className="login-input-wrapper">
                        <input
                            id="password"
                            type={showPassword ? 'text' : 'password'}
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Votre mot de passe"
                        />
                        <button
                            type="button"
                            className="password-toggle"
                            onClick={() => setShowPassword((v) => !v)}
                            aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                        >
                            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                    </div>
                    <p className="forgot-link"><a href="/forgot-password">Mot de passe oublié ?</a></p>
                </div>

                <label className="login-remember">
                    <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                    Rester connecté sur cet appareil
                </label>

                <button type="submit" className="login-submit" disabled={loading}>
                    {loading ? 'Connexion...' : 'Se connecter'}
                </button>
            </form>
        </div>
    );
}