import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

function currentMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

// Données du Portefeuille : solde, bilan du mois choisi, historique détaillé et numéros
// mobile money déjà utilisés.
export function useWalletData() {
    const [solde, setSolde] = useState(null);
    const [mois, setMois] = useState(currentMonth());
    const [resume, setResume] = useState(null);
    const [historique, setHistorique] = useState([]);
    const [numeros, setNumeros] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchAll = useCallback(() => {
        setError('');
        return Promise.all([
            api.get('/wallet/solde'),
            api.get('/wallet/historique'),
            api.get('/wallet/numeros').catch(() => ({ data: [] })),
        ])
            .then(([soldeRes, histRes, numRes]) => {
                setSolde(soldeRes.data.solde);
                setHistorique(Array.isArray(histRes.data) ? histRes.data : []);
                setNumeros(Array.isArray(numRes.data) ? numRes.data : []);
            })
            .catch(() => setError('Impossible de charger votre portefeuille. Réessayez dans un instant.'))
            .finally(() => setLoading(false));
    }, []);

    const fetchResume = useCallback(() => {
        return api.get('/wallet/resume', { params: { mois } })
            .then((res) => setResume(res.data))
            .catch(() => setResume(null));
    }, [mois]);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    useEffect(() => {
        fetchResume();
    }, [fetchResume]);

    async function refresh() {
        await Promise.all([fetchAll(), fetchResume()]);
    }

    async function recharger(phone_number, network, montant) {
        const res = await api.post('/wallet/recharger', { phone_number, network, montant });
        await refresh();
        return res.data;
    }

    async function retirer(phone_number, network, montant, password) {
        try {
            const res = await api.post('/wallet/retirer', { phone_number, network, montant, password });
            return res.data;
        } finally {
            await refresh();
        }
    }

    async function telechargerReleve() {
        const res = await api.get('/wallet/releve.csv', { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `releve-miabewifi-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }

    return {
        solde, mois, setMois, resume, historique, numeros, loading, error,
        refresh, recharger, retirer, telechargerReleve,
    };
}
