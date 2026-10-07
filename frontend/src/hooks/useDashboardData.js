import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

// Données du tableau de bord : routeurs (avec état et clients connectés), ventes du jour,
// alertes de stock, solde et montant réservé par un retrait en vérification.
export function useDashboardData() {
    const [solde, setSolde] = useState(null);
    const [reserve, setReserve] = useState(0);
    const [routers, setRouters] = useState([]);
    const [statuses, setStatuses] = useState({});   // { [id]: {connecte} | null }
    const [clients, setClients] = useState({});     // { [id]: nombre | null }
    const [resume, setResume] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchAll = useCallback(() => {
        return Promise.all([
            api.get('/wallet/solde'),
            api.get('/routers/'),
            api.get('/dashboard/resume').catch(() => ({ data: null })),
            api.get('/wallet/resume').catch(() => ({ data: null })),
        ])
            .then(([soldeRes, routersRes, resumeRes, walletRes]) => {
                setSolde(soldeRes.data.solde);
                setRouters(routersRes.data);
                setResume(resumeRes.data);
                setReserve(walletRes.data?.reserve || 0);
                routersRes.data.forEach((r) => {
                    api.get(`/routers/${r.id}/status`)
                        .then((res) => {
                            setStatuses((prev) => ({ ...prev, [r.id]: res.data }));
                            if (!res.data?.connecte) {
                                setClients((prev) => ({ ...prev, [r.id]: null }));
                                return;
                            }
                            api.get(`/hotspot/${r.id}/sessions`)
                                .then((s) => setClients((prev) => ({ ...prev, [r.id]: Array.isArray(s.data) ? s.data.length : null })))
                                .catch(() => setClients((prev) => ({ ...prev, [r.id]: null })));
                        })
                        .catch(() => setStatuses((prev) => ({ ...prev, [r.id]: null })));
                });
            })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    return { solde, reserve, routers, statuses, clients, resume, loading, refresh: fetchAll };
}
