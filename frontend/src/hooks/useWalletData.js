import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useWalletData() {
    const [solde, setSolde] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAll = useCallback(() => {
        setLoading(true);
        return Promise.all([api.get('/wallet/solde'), api.get('/wallet/transactions')])
            .then(([soldeRes, txRes]) => {
                setSolde(soldeRes.data.solde);
                setTransactions(txRes.data);
            })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    async function recharger(phone_number, network, montant) {
        const res = await api.post('/wallet/recharger', { phone_number, network, montant });
        await fetchAll();
        return res.data;
    }

    async function retirer(phone_number, network, montant) {
        const res = await api.post('/wallet/retirer', { phone_number, network, montant });
        await fetchAll();
        return res.data;
    }

    return { solde, transactions, loading, fetchAll, recharger, retirer };
}