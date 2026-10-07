import { useMemo, useState } from 'react';
import { Plus, Ticket } from 'lucide-react';
import { useHotspotDashboard } from '../../hooks/useHotspotDashboard';
import { confirmDialog } from '../../utils/confirm';
import { formatAmount } from '../../utils/format';
import RouterPicker from './RouterPicker';
import TicketsTab from './TicketsTab';
import ForfaitsTab from './ForfaitsTab';
import ForfaitModal from './ForfaitModal';
import WifiPageTab from './WifiPageTab';
import SettingsTab from './SettingsTab';
import LiveTab from './LiveTab';
import SellTicketModal from './SellTicketModal';
import CreateTicketsWizard from './CreateTicketsWizard';
import { errorMessage, groupBatches, isSameDay, sellableProfiles } from './hotspotUtils';
import './HotspotTickets.css';

const TABS = [
    { key: 'tickets', label: 'Mes tickets' },
    { key: 'forfaits', label: 'Forfaits et prix' },
    { key: 'wifi', label: 'Page Wi-Fi' },
    { key: 'live', label: 'En direct' },
    { key: 'reglages', label: 'Réglages' },
];

// Page « Tickets hotspots » : chiffres clés, vente rapide, création guidée,
// et quatre onglets pour séparer le quotidien des réglages.
export default function HotspotTickets({ onGoToRouters, initialTab }) {
    const data = useHotspotDashboard();
    const {
        routers, selectedRouterId, setSelectedRouterId, batches, profiles, settings, loading, error,
        routerStatuses, forfaitSettings, sales, connectedClients, currentRateLimit,
    } = data;

    const [tab, setTab] = useState(initialTab || 'tickets');
    const [busy, setBusy] = useState(false);
    const [actionError, setActionError] = useState('');
    const [actionInfo, setActionInfo] = useState('');
    const [sellKey, setSellKey] = useState(undefined);       // undefined = fermé
    const [wizardProfile, setWizardProfile] = useState(undefined);
    const [forfaitEdit, setForfaitEdit] = useState(undefined); // { profile, setting } | {} pour un nouveau

    const groups = useMemo(() => groupBatches(batches, profiles), [batches, profiles]);

    const stats = useMemo(() => {
        const now = new Date();
        const today = sales.filter((s) => isSameDay(new Date(s.vendu_le), now));
        const month = sales.filter((s) => {
            const d = new Date(s.vendu_le);
            return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
        });
        return {
            disponibles: groups.reduce((n, g) => n + g.disponibles, 0),
            vendusAujourdhui: today.length,
            recettesMois: month.reduce((sum, s) => sum + (Number(s.montant) || 0), 0),
        };
    }, [groups, sales]);

    function onMessage(err, info) {
        setActionError(err);
        setActionInfo(info);
    }

    function selectRouter(id) {
        onMessage('', '');
        setSelectedRouterId(id);
    }

    async function handleSaveForfait(values) {
        const { profile } = forfaitEdit;
        if (profile) {
            await data.updateProfile(profile['.id'], {
                duree_valeur: values.duree_valeur,
                duree_unite: values.duree_unite,
                partage: values.partage,
                rate_limit: values.rate_limit,
            });
        } else {
            await data.createProfile(values.name, values.duree_valeur, values.duree_unite, values.partage, values.rate_limit);
        }
        await data.saveForfaitSetting(profile ? profile.name : values.name, {
            prix: values.prix,
            validite_jours: values.validite_jours,
            quota_mo: values.quota_mo,
        });
        setForfaitEdit(undefined);
        onMessage('', profile ? 'Forfait modifié.' : 'Forfait créé. Vous pouvez maintenant créer des tickets avec ce forfait.');
    }

    async function handleDeleteForfait(profile) {
        if (!(await confirmDialog(`Supprimer le forfait « ${profile.name} » ? Les tickets déjà créés avec ce forfait continueront de fonctionner.`, { confirmLabel: 'Supprimer', danger: true }))) return;
        setBusy(true);
        onMessage('', '');
        try {
            await data.deleteProfile(profile['.id']);
            await data.deleteForfaitSetting(profile.name);
            onMessage('', 'Forfait supprimé.');
        } catch (err) {
            onMessage(errorMessage(err, 'Impossible de supprimer ce forfait.'), '');
        } finally {
            setBusy(false);
        }
    }

    if (!loading && routers.length === 0) {
        return (
            <div className="section-card hs-empty">
                <Ticket size={28} />
                <h2>Pas encore de routeur</h2>
                <p className="empty-hint">Ajoutez d'abord un routeur pour pouvoir créer et vendre des tickets.</p>
                {onGoToRouters && <button type="button" className="btn-primary" onClick={onGoToRouters}>Ajouter un routeur</button>}
            </div>
        );
    }

    return (
        <div className="hs-page">
            <div className="hs-top">
                <RouterPicker
                    routers={routers}
                    selectedRouterId={selectedRouterId}
                    onSelect={selectRouter}
                    statuses={routerStatuses}
                    onGoToRouters={onGoToRouters}
                />
                <div className="hs-top-actions">
                    <button type="button" className="btn-primary" disabled={!selectedRouterId || stats.disponibles === 0} onClick={() => setSellKey(null)}>
                        <Ticket size={16} /> Vendre un ticket
                    </button>
                    <button type="button" className="btn-secondary" disabled={!selectedRouterId} onClick={() => setWizardProfile(null)}>
                        <Plus size={16} /> Créer des tickets
                    </button>
                </div>
            </div>

            <div className="hs-stats">
                <div className="hs-stat"><span>Tickets disponibles</span><b>{formatAmount(stats.disponibles)}</b></div>
                <div className="hs-stat"><span>Vendus aujourd'hui</span><b>{formatAmount(stats.vendusAujourdhui)}</b></div>
                <div className="hs-stat"><span>Recettes du mois</span><b>{formatAmount(stats.recettesMois)} F</b></div>
                <button type="button" className="hs-stat hs-stat-btn" onClick={() => { setTab('live'); onMessage('', ''); }} title="Voir les clients connectés">
                    <span>Clients connectés</span><b>{connectedClients === null ? '—' : connectedClients}</b>
                </button>
            </div>

            <div className="hs-tabs" role="tablist">
                {TABS.map((t) => (
                    <button
                        key={t.key}
                        type="button"
                        role="tab"
                        aria-selected={tab === t.key}
                        className={`hs-tab${tab === t.key ? ' is-on' : ''}`}
                        onClick={() => { setTab(t.key); onMessage('', ''); }}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {actionError && <p className="error-text">{actionError}</p>}
            {actionInfo && <p className="success-text">{actionInfo}</p>}
            {error && <p className="error-text">{error}</p>}

            {tab === 'tickets' && (
                <TicketsTab
                    groups={groups}
                    batches={batches}
                    loading={loading}
                    busy={busy}
                    setBusy={setBusy}
                    onMessage={onMessage}
                    onOpenSell={(key) => setSellKey(key)}
                    onOpenWizard={(profileName) => setWizardProfile(profileName || null)}
                    onSellVoucher={data.sellVoucher}
                    onDeleteVoucher={data.deleteVoucher}
                    onDeleteBatch={data.deleteBatch}
                    onDownload={data.downloadBatchPdf}
                    onSetGroupOnline={data.setGroupOnline}
                />
            )}

            {tab === 'forfaits' && (
                <ForfaitsTab
                    profiles={sellableProfiles(profiles)}
                    forfaitSettings={forfaitSettings}
                    busy={busy}
                    onNew={() => setForfaitEdit({})}
                    onEdit={(profile, setting) => setForfaitEdit({ profile, setting })}
                    onDelete={handleDeleteForfait}
                />
            )}

            {tab === 'wifi' && settings && (
                <WifiPageTab
                    key={selectedRouterId}
                    settings={settings}
                    groups={groups}
                    busy={busy}
                    setBusy={setBusy}
                    onMessage={onMessage}
                    onSaveSettings={data.saveSettings}
                    onInstall={data.installLoginPage}
                    onUploadLogo={data.uploadLogo}
                    onRemoveLogo={data.removeLogo}
                    onUploadBackground={data.uploadBackground}
                    onRemoveBackground={data.removeBackground}
                />
            )}

            {tab === 'live' && <LiveTab key={selectedRouterId} routerId={selectedRouterId} />}

            {tab === 'reglages' && settings && (
                <SettingsTab
                    key={selectedRouterId}
                    settings={settings}
                    currentRateLimit={currentRateLimit}
                    busy={busy}
                    setBusy={setBusy}
                    onMessage={onMessage}
                    onSaveSettings={data.saveSettings}
                    onApplyRate={data.applyRateLimit}
                    onSync={data.refreshAll}
                />
            )}

            {(tab === 'wifi' || tab === 'reglages') && !settings && <p className="empty-hint">Chargement des réglages…</p>}

            {sellKey !== undefined && (
                <SellTicketModal
                    groups={groups}
                    initialKey={sellKey}
                    onSell={data.sellVoucher}
                    onClose={() => setSellKey(undefined)}
                />
            )}

            {wizardProfile !== undefined && (
                <CreateTicketsWizard
                    profiles={sellableProfiles(profiles)}
                    forfaitSettings={forfaitSettings}
                    groups={groups}
                    initialProfileName={wizardProfile}
                    onlineSalesEnabled={Boolean(settings?.online_sales_enabled)}
                    onCreate={(p) => data.generateBatch(p.profile_name, p.prix, p.quantite, p.validite_jours, p.quota_mo)}
                    onSavePrice={data.saveForfaitSetting}
                    onSetOnline={data.setBatchOnlineSale}
                    onDownload={data.downloadBatchPdf}
                    onNewForfait={() => { setWizardProfile(undefined); setTab('forfaits'); setForfaitEdit({}); }}
                    onClose={() => setWizardProfile(undefined)}
                />
            )}

            {forfaitEdit !== undefined && (
                <ForfaitModal
                    profile={forfaitEdit.profile}
                    setting={forfaitEdit.setting}
                    defaultRate={currentRateLimit}
                    onSave={handleSaveForfait}
                    onClose={() => setForfaitEdit(undefined)}
                />
            )}
        </div>
    );
}
