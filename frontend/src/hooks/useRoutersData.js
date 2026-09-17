import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useRoutersData() {
    const [routers, setRouters] = useState([]);
    const [packs, setPacks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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

    return { routers, packs, loading, error, fetchAll, createRouter, deleteRouter, regenerateRouter, activerPack };
}