import { useState, useEffect } from 'react';
import api from '../api/client';

export function useAuth() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('miabewifi_token') || sessionStorage.getItem('miabewifi_token');
        if (!token) {
            setLoading(false);
            return;
        }
        api.get('/auth/me')
            .then((res) => setUser(res.data))
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, []);
    function logout() {
        localStorage.removeItem('miabewifi_token');
        sessionStorage.removeItem('miabewifi_token');
        window.location.href = '/login';
    }

    return { user, loading, isAdmin: user?.role === 'admin', logout };
}