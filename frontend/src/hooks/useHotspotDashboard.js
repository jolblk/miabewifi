import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';
import { useHotspotData } from './useHotspotData';

// Données de la page « Tickets hotspots » : tout ce que fournit useHotspotData (routeurs, lots,
// forfaits, réglages), plus l'état de chaque routeur, les prix par forfait, les ventes et le
// nombre de clients connectés.
export function useHotspotDashboard() {
    const base = useHotspotData();
    const { routers, selectedRouterId } = base;

    const [routerStatuses, setRouterStatuses] = useState({}); // { [id]: {connecte, actif} | null }
    const [forfaitSettings, setForfaitSettings] = useState([]);
    const [sales, setSales] = useState([]);
    const [connectedClients, setConnectedClients] = useState(null);

    const fetchStatuses = useCallback(() => {
        routers.forEach((r) => {
            api.get(`/routers/${r.id}/status`)
                .then((res) => setRouterStatuses((prev) => ({ ...prev, [r.id]: res.data })))
                .catch(() => setRouterStatuses((prev) => ({ ...prev, [r.id]: null })));
        });
    }, [routers]);

    useEffect(() => {
        fetchStatuses();
        const timer = setInterval(fetchStatuses, 60000);
        return () => clearInterval(timer);
    }, [fetchStatuses]);

    const fetchForfaitSettings = useCallback(() => {
        if (!selectedRouterId) {
            setForfaitSettings([]);
            return Promise.resolve();
        }
        return api.get(`/hotspot/${selectedRouterId}/forfait-settings`)
            .then((res) => setForfaitSettings(Array.isArray(res.data) ? res.data : []))
            .catch(() => setForfaitSettings([]));
    }, [selectedRouterId]);

    const fetchSales = useCallback(() => {
        if (!selectedRouterId) {
            setSales([]);
            return Promise.resolve();
        }
        return api.get(`/hotspot/${selectedRouterId}/sales`)
            .then((res) => setSales(Array.isArray(res.data) ? res.data : []))
            .catch(() => setSales([]));
    }, [selectedRouterId]);

    const fetchConnectedClients = useCallback(() => {
        if (!selectedRouterId) {
            setConnectedClients(null);
            return Promise.resolve();
        }
        setConnectedClients(null);
        return api.get(`/hotspot/${selectedRouterId}/sessions`)
            .then((res) => setConnectedClients(Array.isArray(res.data) ? res.data.length : null))
            .catch(() => setConnectedClients(null));
    }, [selectedRouterId]);

    useEffect(() => {
        fetchForfaitSettings();
        fetchSales();
        fetchConnectedClients();
    }, [fetchForfaitSettings, fetchSales, fetchConnectedClients]);

    async function saveForfaitSetting(profileName, setting) {
        const res = await api.put(
            `/hotspot/${selectedRouterId}/forfait-settings/${encodeURIComponent(profileName)}`,
            setting,
        );
        await fetchForfaitSettings();
        return res.data;
    }

    async function deleteForfaitSetting(profileName) {
        try {
            await api.delete(`/hotspot/${selectedRouterId}/forfait-settings/${encodeURIComponent(profileName)}`);
        } catch {
            // aucun prix enregistré : rien à faire
        }
        await fetchForfaitSettings();
    }

    async function sellVoucher(voucherId) {
        const voucher = await base.sellVoucher(voucherId);
        await fetchSales();
        return voucher;
    }

    async function setGroupOnline(group, online) {
        for (const batch of group.batches) {
            if ((batch.online_sale !== false) !== online) {
                await base.setBatchOnlineSale(batch.id, online);
            }
        }
    }

    async function refreshAll() {
        const res = await base.syncNow();
        await Promise.all([fetchSales(), fetchConnectedClients()]);
        fetchStatuses();
        return res;
    }

    return {
        ...base,
        routerStatuses,
        forfaitSettings,
        sales,
        connectedClients,
        saveForfaitSetting,
        deleteForfaitSetting,
        sellVoucher,
        setGroupOnline,
        refreshAll,
    };
}
