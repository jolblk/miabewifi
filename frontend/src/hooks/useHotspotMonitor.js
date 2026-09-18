import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useHotspotMonitor() {
    const [routers, setRouters] = useState([]);
    const [selectedRouterId, setSelectedRouterId] = useState(null);
    const [users, setUsers] = useState([]);
    const [profiles, setProfiles] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        api.get('/routers/')
            .then((res) => {
                setRouters(res.data);
                if (res.data.length > 0) setSelectedRouterId(res.data[0].id);
            })
            .catch(() => setError("Impossible de charger vos routeurs."))
            .finally(() => setLoading(false));
    }, []);

    const fetchAll = useCallback(() => {
        if (!selectedRouterId) {
            setUsers([]);
            setProfiles([]);
            setSessions([]);
            return;
        }
        setLoading(true);
        setError(null);
        Promise.all([
            api.get(`/hotspot/${selectedRouterId}/users`),
            api.get(`/hotspot/${selectedRouterId}/profiles`),
            api.get(`/hotspot/${selectedRouterId}/sessions`),
        ])
            .then(([usersRes, profilesRes, sessionsRes]) => {
                setUsers(Array.isArray(usersRes.data) ? usersRes.data : []);
                setProfiles(Array.isArray(profilesRes.data) ? profilesRes.data : []);
                setSessions(Array.isArray(sessionsRes.data) ? sessionsRes.data : []);
            })
            .catch((err) => {
                setError(err.response?.data?.detail || "Impossible de joindre ce routeur.");
                setUsers([]);
                setProfiles([]);
                setSessions([]);
            })
            .finally(() => setLoading(false));
    }, [selectedRouterId]);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    return {
        routers, selectedRouterId, setSelectedRouterId,
        users, profiles, sessions,
        loading, error, refresh: fetchAll,
    };
}