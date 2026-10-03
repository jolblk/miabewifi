import { useEffect, useRef, useState } from 'react';
import { registerConfirmListener } from '../utils/confirm';
import './ConfirmHost.css';

export default function ConfirmHost() {
    const [request, setRequest] = useState(null);
    const confirmRef = useRef(null);

    useEffect(() => {
        return registerConfirmListener((req) => {
            setRequest((previous) => {
                if (previous) previous.resolve(false);
                return req;
            });
        });
    }, []);

    useEffect(() => {
        if (!request) return;
        confirmRef.current?.focus();
        function onKey(e) {
            if (e.key === 'Escape') close(false);
        }
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    });

    function close(result) {
        if (!request) return;
        request.resolve(result);
        setRequest(null);
    }

    if (!request) return null;

    return (
        <div className="confirm-overlay" onClick={() => close(false)}>
            <div
                className="confirm-box"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                <p className="confirm-message">{request.message}</p>
                <div className="confirm-actions">
                    <button type="button" className="btn-secondary" onClick={() => close(false)}>
                        {request.cancelLabel || 'Annuler'}
                    </button>
                    <button
                        type="button"
                        ref={confirmRef}
                        className={request.danger ? 'btn-primary confirm-danger' : 'btn-primary'}
                        onClick={() => close(true)}
                    >
                        {request.confirmLabel || 'Confirmer'}
                    </button>
                </div>
            </div>
        </div>
    );
}
