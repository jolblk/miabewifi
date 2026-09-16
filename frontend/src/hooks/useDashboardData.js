import { useState, useEffect } from 'react';
import api from '../api/client';

export function useDashboardData() {
    const [solde, setSolde] = useState(null);
    const [routers, setRouters] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([api.get('/wallet/solde'), api.get('/routers/')])
            .then(([soldeRes, routersRes]) => {
                setSolde(soldeRes.data.solde);
                setRouters(routersRes.data);
            })
            .finally(() => setLoading(false));
    }, []);

    const now = new Date();

    const actifs = routers.filter((r) => {
        const trial = r.trial_expires_at && new Date(r.trial_expires_at) > now;
        const abo = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
        return trial || abo;
    });

    const prochaineEcheance = routers
        .map((r) => (r.subscription_expires_at ? new Date(r.subscription_expires_at) : null))
        .filter((d) => d && d > now)
        .sort((a, b) => a - b)[0] || null;

    const dans7j = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    const echeancesProches = routers.filter((r) => {
        const d = r.subscription_expires_at ? new Date(r.subscription_expires_at) : null;
        return d && d > now && d <= dans7j;
    });

    const aSurveiller = routers.filter((r) => {
        const trial = r.trial_expires_at && new Date(r.trial_expires_at) > now;
        const abo = r.subscription_expires_at && new Date(r.subscription_expires_at) > now;
        return !trial && !abo;
    });

    return { solde, routers, actifs, prochaineEcheance, echeancesProches, aSurveiller, loading };
}