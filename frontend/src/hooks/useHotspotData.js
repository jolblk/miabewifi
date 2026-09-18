import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useHotspotData() {
    const [routers, setRouters] = useState([]);
    const [selectedRouterId, setSelectedRouterId] = useState(null);
    const [batches, setBatches] = useState([]);
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

    const fetchBatches = useCallback(() => {
        if (!selectedRouterId) {
            setBatches([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        api.get(`/hotspot/${selectedRouterId}/vouchers`)
            .then((res) => setBatches(Array.isArray(res.data) ? res.data : []))
            .catch(() => {
                setError("Impossible de charger les tickets de ce routeur.");
                setBatches([]);
            })
            .finally(() => setLoading(false));
    }, [selectedRouterId]);

    useEffect(() => {
        fetchBatches();
    }, [fetchBatches]);

    async function generateBatch(profileName, prixUnitaire, quantite) {
        const res = await api.post(`/hotspot/${selectedRouterId}/vouchers`, {
            profile_name: profileName,
            prix_unitaire: prixUnitaire,
            quantite,
        });
        await fetchBatches();
        return res.data;
    }

    async function sellVoucher(voucherId) {
        const res = await api.post(`/hotspot/vouchers/${voucherId}/sell`, {});
        await fetchBatches();
        return res.data;
    }

    async function downloadBatchPdf(batchId) {
        const res = await api.get(`/hotspot/vouchers/batch/${batchId}/pdf`, { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `tickets-${batchId}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }

    return {
        routers, selectedRouterId, setSelectedRouterId,
        batches, loading, error,
        generateBatch, sellVoucher, downloadBatchPdf,
    };
}