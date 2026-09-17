import { useState } from 'react';
import { Send } from 'lucide-react';
import api from '../api/client';

export default function Support() {
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
            <h1 className="page-title">Support</h1>
            <p className="greeting">Une question ou un problème ? Écrivez-nous, nous répondons rapidement.</p>

            <div className="section-card">
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
        </div>
    );
}