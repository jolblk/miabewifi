import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { LogOut, Send, User, HelpCircle } from 'lucide-react';
import api from '../api/client';
import './Account.css';

export default function Account() {
    const { user, logout } = useOutletContext();
    const [tab, setTab] = useState('profil');

    return (
        <div>
            <h1 className="page-title">Mon compte</h1>

            <div className="section-card">
                <div className="account-tabs">
                    <button
                        className={`account-tab ${tab === 'profil' ? 'active' : ''}`}
                        onClick={() => setTab('profil')}
                    >
                        <User size={16} /> Profil
                    </button>
                    <button
                        className={`account-tab ${tab === 'support' ? 'active' : ''}`}
                        onClick={() => setTab('support')}
                    >
                        <HelpCircle size={16} /> Support
                    </button>
                </div>

                {tab === 'profil' ? (
                    <ProfilTab user={user} logout={logout} />
                ) : (
                    <SupportTab />
                )}
            </div>
        </div>
    );
}

function ProfilTab({ user, logout }) {
    return (
        <div>
            <div className="router-meta" style={{ marginBottom: 16 }}>
                <span>Nom : <strong>{user?.nom}</strong></span>
                <span>Email : <strong>{user?.email}</strong></span>
            </div>

            <button className="btn-danger" onClick={logout}>
                <LogOut size={16} /> Déconnexion
            </button>
        </div>
    );
}

function SupportTab() {
    const [telephone, setTelephone] = useState('');
    const [message, setMessage] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!message.trim()) {
            setError('Le message ne peut pas être vide.');
            return;
        }
        setBusy(true);
        try {
            const res = await api.post('/support/contact', {
                telephone: telephone.trim() || undefined,
                message: message.trim(),
            });
            setSuccess(res.data.message || 'Message envoyé avec succès.');
            setMessage('');
            setTelephone('');
        } catch (err) {
            setError(err.response?.data?.detail || "Impossible d'envoyer le message pour le moment.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div>
            <p className="greeting">Une question ou un problème ? Écrivez-nous, nous répondons rapidement.</p>

            {error && <p className="error-text">{error}</p>}
            {success && <p className="success-text">{success}</p>}

            <form className="form-stack" onSubmit={handleSubmit} style={{ maxWidth: 480 }}>
                <div>
                    <label className="field-label" htmlFor="telephone">Téléphone (optionnel)</label>
                    <input
                        id="telephone"
                        type="tel"
                        className="text-input"
                        style={{ width: '100%' }}
                        value={telephone}
                        onChange={(e) => setTelephone(e.target.value)}
                        placeholder="Ex : 90000000"
                    />
                </div>

                <div>
                    <label className="field-label" htmlFor="message">Votre message</label>
                    <textarea
                        id="message"
                        className="text-input"
                        style={{ width: '100%', minHeight: 120, resize: 'vertical', fontFamily: 'inherit' }}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Décrivez votre problème ou votre question..."
                    />
                </div>

                <button className="btn-primary" type="submit" disabled={busy}>
                    <Send size={16} /> Envoyer
                </button>
            </form>
        </div>
    );
}