import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useRoutersData() {
    const [routers, setRouters] = useState([]);
    const [packs, setPacks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState({}); // { [routerId]: {connecte, actif} | null }

    const fetchAll = useCallback(() => {
        setLoading(true);
        setError(null);
        return Promise.all([api.get('/routers/'), api.get('/packs/')])
            .then(([routersRes, packsRes]) => {
                setRouters(routersRes.data);
                setPacks(packsRes.data);
            })
            .catch(() => setError("Impossible de charger vos routeurs."))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    // Sonde l'état de connexion de chaque routeur, comme le badge "Essai" mais
    // pour le tunnel WireGuard. `null` = sondage en échec, `undefined` = pas encore reçu.
    useEffect(() => {
        if (routers.length === 0) return undefined;

        let cancelled = false;
        const poll = () => {
            routers.forEach((r) => {
                api.get(`/routers/${r.id}/status`)
                    .then((res) => {
                        if (!cancelled) setConnectionStatus((prev) => ({ ...prev, [r.id]: res.data }));
                    })
                    .catch(() => {
                        if (!cancelled) setConnectionStatus((prev) => ({ ...prev, [r.id]: null }));
                    });
            });
        };

        poll();
        const interval = setInterval(poll, 20000);
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [routers]);

    async function createRouter(nom) {
        const res = await api.post('/routers/', { nom });
        await fetchAll();
        return res.data;
    }

    async function deleteRouter(routerId) {
        await api.delete(`/routers/${routerId}`);
        await fetchAll();
    }

    async function regenerateRouter(routerId) {
        const res = await api.post(`/routers/${routerId}/regenerate`);
        await fetchAll();
        return res.data;
    }

    async function activerPack(routerId, packId) {
        const res = await api.post(`/routers/${routerId}/activer-pack`, { pack_id: packId });
        await fetchAll();
        return res.data;
    }

    async function setMikrotikCredentials(routerId, apiUsername, apiPassword) {
        const res = await api.patch(`/routers/${routerId}/mikrotik-credentials`, {
            api_username: apiUsername,
            api_password: apiPassword,
        });
        await fetchAll();
        return res.data;
    }

    return { routers, packs, loading, error, connectionStatus, fetchAll, createRouter, deleteRouter, regenerateRouter, activerPack, setMikrotikCredentials };
}