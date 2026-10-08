import { useState } from 'react';
import { KeyRound, LogOut, ShieldCheck } from 'lucide-react';
import api, { isRememberedSession, replaceToken } from '../api/client';
import { getErrorMessage } from '../utils/errorMessage';
import { confirmDialog } from '../utils/confirm';
import './SecuritySettings.css';

// Bloc « Sécurité » du profil : changer son mot de passe, se déconnecter de tous les appareils.
export default function SecuritySettings() {
    return (
        <div className="security-settings">
            <ChangePasswordForm />
            <LogoutEverywhere />
        </div>
    );
}

function ChangePasswordForm() {
    const [current, setCurrent] = useState('');
    const [next, setNext] = useState('');
    const [confirm, setConfirm] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (next.length < 8) return setError('Le nouveau mot de passe doit contenir au moins 8 caractères.');
        if (next !== confirm) return setError('Les deux nouveaux mots de passe ne sont pas identiques.');
        if (next === current) return setError("Le nouveau mot de passe doit être différent de l'actuel.");
        setBusy(true);
        try {
            const res = await api.post('/auth/change-password', {
                current_password: current,
                new_password: next,
                remember: isRememberedSession(),
            });
            // Les autres appareils sont déconnectés ; celui-ci reçoit une nouvelle connexion.
            replaceToken(res.data.access_token);
            setCurrent('');
            setNext('');
            setConfirm('');
            setSuccess('Mot de passe changé. Vos autres appareils ont été déconnectés.');
        } catch (err) {
            setError(getErrorMessage(err, "Le mot de passe n'a pas pu être changé."));
        } finally {
            setBusy(false);
        }
    }

    return (
        <form className="form-stack security-block" onSubmit={handleSubmit}>
            <h2 className="security-title"><KeyRound size={18} /> Changer mon mot de passe</h2>

            <div>
                <label className="field-label" htmlFor="sec-current">Mot de passe actuel</label>
                <input
                    id="sec-current"
                    type="password"
                    className="text-input"
                    autoComplete="current-password"
                    required
                    value={current}
                    onChange={(e) => setCurrent(e.target.value)}
                />
            </div>
            <div>
                <label className="field-label" htmlFor="sec-new">Nouveau mot de passe (8 caractères minimum)</label>
                <input
                    id="sec-new"
                    type="password"
                    className="text-input"
                    autoComplete="new-password"
                    minLength={8}
                    required
                    value={next}
                    onChange={(e) => setNext(e.target.value)}
                />
            </div>
            <div>
                <label className="field-label" htmlFor="sec-confirm">Confirmer le nouveau mot de passe</label>
                <input
                    id="sec-confirm"
                    type="password"
                    className="text-input"
                    autoComplete="new-password"
                    minLength={8}
                    required
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                />
            </div>

            {error && <p className="error-text" role="alert">{error}</p>}
            {success && <p className="success-text" role="status"><ShieldCheck size={16} /> {success}</p>}

            <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? 'Enregistrement…' : 'Changer le mot de passe'}
            </button>
        </form>
    );
}

function LogoutEverywhere() {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    async function handleClick() {
        const ok = await confirmDialog(
            'Vous serez déconnecté de tous vos appareils, y compris celui-ci. Il faudra vous reconnecter avec votre mot de passe.',
            { confirmLabel: 'Tout déconnecter', danger: true },
        );
        if (!ok) return;
        setBusy(true);
        setError('');
        try {
            await api.post('/auth/logout-all');
            localStorage.removeItem('miabewifi_token');
            sessionStorage.removeItem('miabewifi_token');
            window.location.href = '/login';
        } catch (err) {
            setError(getErrorMessage(err, "La déconnexion n'a pas pu être effectuée."));
            setBusy(false);
        }
    }

    return (
        <div className="security-block">
            <h2 className="security-title"><LogOut size={18} /> Appareils connectés</h2>
            <p className="security-hint">
                Téléphone perdu, ordinateur partagé resté connecté ? Coupez toutes les connexions ouvertes
                avec votre compte.
            </p>
            {error && <p className="error-text" role="alert">{error}</p>}
            <button className="btn-secondary" type="button" onClick={handleClick} disabled={busy}>
                {busy ? 'Déconnexion…' : 'Se déconnecter de tous les appareils'}
            </button>
        </div>
    );
}
