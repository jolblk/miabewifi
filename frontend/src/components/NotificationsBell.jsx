import { useState, useEffect, useRef } from 'react';
import { Bell } from 'lucide-react';
import api from '../api/client';
import './NotificationsBell.css';

const typeClass = { expiring: 'notif-warning', expired: 'notif-danger', info: 'notif-info' };

export default function NotificationsBell() {
    const [notifications, setNotifications] = useState([]);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(true);
    const ref = useRef(null);

    useEffect(() => {
        api.get('/notifications/')
            .then((res) => setNotifications(res.data))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        function handleClickOutside(e) {
            if (ref.current && !ref.current.contains(e.target)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="notif-wrapper" ref={ref}>
            <button className="notif-bell" onClick={() => setOpen((v) => !v)} aria-label="Notifications">
                <Bell size={20} />
                {notifications.length > 0 && <span className="notif-badge">{notifications.length}</span>}
            </button>

            {open && (
                <div className="notif-panel">
                    <div className="notif-panel-header">Notifications</div>
                    {loading && <p className="empty-hint" style={{ padding: '0 14px 14px' }}>Chargement...</p>}
                    {!loading && notifications.length === 0 && (
                        <p className="empty-hint" style={{ padding: '0 14px 14px' }}>Aucune notification.</p>
                    )}
                    <div className="notif-list">
                        {notifications.map((n) => (
                            <div key={n.id} className={`notif-item ${typeClass[n.type] || ''}`}>
                                <div className="notif-title">{n.title}</div>
                                <div className="notif-message">{n.message}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}