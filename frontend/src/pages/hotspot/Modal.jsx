import { useEffect } from 'react';
import { X } from 'lucide-react';

// Fenêtre par-dessus la page. Échap ou un clic sur le fond la ferment.
export default function Modal({ title, onClose, children, width = 440 }) {
    useEffect(() => {
        function onKey(e) {
            if (e.key === 'Escape') onClose();
        }
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [onClose]);

    return (
        <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div className="modal-box hs-modal" style={{ maxWidth: width }} role="dialog" aria-modal="true" aria-label={title}>
                <div className="hs-modal-head">
                    <h2>{title}</h2>
                    <button type="button" className="icon-btn" onClick={onClose} aria-label="Fermer">
                        <X size={18} />
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
}
