import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export function useHotspotData() {
    const [routers, setRouters] = useState([]);
    const [selectedRouterId, setSelectedRouterId] = useState(null);
    const [batches, setBatches] = useState([]);
    const [profiles, setProfiles] = useState([]);
    // Réglages rattachés au routeur pour lequel ils ont été chargés : en changeant de routeur,
    // on n'affiche jamais ceux du précédent le temps du chargement.
    const [settingsState, setSettingsState] = useState({ routerId: null, data: null });
    const settings = settingsState.routerId === selectedRouterId ? settingsState.data : null;
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

    const fetchSettings = useCallback(() => {
        if (!selectedRouterId) return Promise.resolve();
        return api.get(`/hotspot/${selectedRouterId}/settings`)
            .then((res) => setSettingsState({ routerId: selectedRouterId, data: res.data }))
            .catch(() => setSettingsState({ routerId: selectedRouterId, data: null }));
    }, [selectedRouterId]);

    useEffect(() => {
        fetchBatches();
    }, [fetchBatches]);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

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

    async function generateBatch(profileName, prixUnitaire, quantite, validiteJours, quotaMo) {
        const res = await api.post(`/hotspot/${selectedRouterId}/vouchers`, {
            profile_name: profileName,
            prix_unitaire: prixUnitaire,
            quantite,
            validite_jours: validiteJours || null,
            quota_mo: quotaMo || null,
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

    async function createProfile(name, dureeValeur, dureeUnite, partage, rateLimit) {
        const res = await api.post(`/hotspot/${selectedRouterId}/profiles`, {
            name,
            duree_valeur: dureeValeur,
            duree_unite: dureeUnite,
            partage,
            rate_limit: rateLimit || null,
        });
        await fetchProfiles();
        return res.data;
    }

    async function updateProfile(profileId, changes) {
        const res = await api.patch(`/hotspot/${selectedRouterId}/profiles/${encodeURIComponent(profileId)}`, changes);
        await fetchProfiles();
        return res.data;
    }

    async function saveSettings(changes) {
        const res = await api.put(`/hotspot/${selectedRouterId}/settings`, changes);
        setSettingsState({ routerId: selectedRouterId, data: res.data });
        return res.data;
    }

    async function uploadLogo(file) {
        const form = new FormData();
        form.append('file', file);
        const res = await api.post(`/hotspot/${selectedRouterId}/settings/logo`, form);
        setSettingsState({ routerId: selectedRouterId, data: res.data });
        return res.data;
    }

    async function removeLogo() {
        const res = await api.delete(`/hotspot/${selectedRouterId}/settings/logo`);
        setSettingsState({ routerId: selectedRouterId, data: res.data });
        return res.data;
    }

    async function setBatchOnlineSale(batchId, onlineSale) {
        const res = await api.patch(`/hotspot/vouchers/batch/${batchId}/online-sale`, { online_sale: onlineSale });
        await fetchBatches();
        return res.data;
    }

    async function deleteProfile(profileId) {
        const res = await api.delete(`/hotspot/${selectedRouterId}/profiles/${profileId}`);
        await fetchProfiles();
        return res.data;
    }

    async function installLoginPage() {
        const res = await api.post(`/hotspot/${selectedRouterId}/login-page`);
        return res.data;
    }

    async function deleteVoucher(voucherId) {
        const res = await api.delete(`/hotspot/vouchers/${voucherId}`);
        await fetchBatches();
        return res.data;
    }

    async function deleteBatch(batchId) {
        const res = await api.delete(`/hotspot/vouchers/batch/${batchId}`);
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
        batches, loading, error, profiles, currentRateLimit, settings,
        generateBatch, sellVoucher, syncNow, applyRateLimit, installLoginPage, downloadBatchPdf,
        deleteVoucher, deleteBatch, createProfile, deleteProfile,
        updateProfile, saveSettings, uploadLogo, removeLogo, setBatchOnlineSale,
    };
}
