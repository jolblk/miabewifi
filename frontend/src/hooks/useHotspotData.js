import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useHotspotData() {
    const [routers, setRouters] = useState([]);
    const [selectedRouterId, setSelectedRouterId] = useState(null);
    const [batches, setBatches] = useState([]);
    const [profiles, setProfiles] = useState([]);
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
            return Promise.resolve();
        }
        setLoading(true);
        setError(null);
        return api.get(`/hotspot/${selectedRouterId}/vouchers`)
            .then((res) => setBatches(Array.isArray(res.data) ? res.data : []))
            .catch(() => {
                setError("Impossible de charger les tickets de ce routeur.");
                setBatches([]);
            })
            .finally(() => setLoading(false));
    }, [selectedRouterId]);

    const fetchProfiles = useCallback(() => {
        if (!selectedRouterId) {
            setProfiles([]);
            return Promise.resolve();
        }
        return api.get(`/hotspot/${selectedRouterId}/profiles`)
            .then((res) => setProfiles(Array.isArray(res.data) ? res.data : []))
            .catch(() => setProfiles([]));
    }, [selectedRouterId]);

    useEffect(() => {
        fetchBatches();
    }, [fetchBatches]);

    useEffect(() => {
        fetchProfiles();
    }, [fetchProfiles]);

    // À l'ouverture d'un routeur, on met discrètement l'état des tickets à jour
    // (connexions détectées, tickets expirés). Une erreur ici n'est pas bloquante.
    useEffect(() => {
        if (!selectedRouterId) return;
        api.post(`/hotspot/${selectedRouterId}/sync`)
            .then(() => fetchBatches())
            .catch(() => {});
    }, [selectedRouterId, fetchBatches]);

    // Limite de vitesse actuellement appliquée aux forfaits "Ticket-*" (ex: "2M/2M").
    const currentRateLimit =
        profiles.find((p) => String(p.name || '').startsWith('Ticket-') && p['rate-limit'])?.['rate-limit'] || '';

    async function generateBatch(profileName, prixUnitaire, quantite, validiteJours) {
        const res = await api.post(`/hotspot/${selectedRouterId}/vouchers`, {
            profile_name: profileName,
            prix_unitaire: prixUnitaire,
            quantite,
            validite_jours: validiteJours || null,
        });
        await fetchBatches();
        return res.data;
    }

    async function sellVoucher(voucherId) {
        const res = await api.post(`/hotspot/vouchers/${voucherId}/sell`, {});
        await fetchBatches();
        return res.data;
    }

    async function syncNow() {
        const res = await api.post(`/hotspot/${selectedRouterId}/sync`);
        await fetchBatches();
        return res.data;
    }

    async function applyRateLimit(rateLimit) {
        const res = await api.post(`/hotspot/${selectedRouterId}/rate-limit`, { rate_limit: rateLimit });
        await fetchProfiles();
        return res.data;
    }

    async function installLoginPage() {
        const res = await api.post(`/hotspot/${selectedRouterId}/login-page`);
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
        batches, loading, error, profiles, currentRateLimit,
        generateBatch, sellVoucher, syncNow, applyRateLimit, installLoginPage, downloadBatchPdf,
    };
}
