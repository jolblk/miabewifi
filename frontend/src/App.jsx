import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import AdminRoute from './layouts/AdminRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import Routers from './pages/Routers';
import Wallet from './pages/Wallet';
import Profile from './pages/Profile';
import Support from './pages/Support';
import Account from './pages/Account';
import Hotspot from './pages/Hotspot';
import HotspotMonitor from './pages/HotspotMonitor';
import AdminOverview from './pages/admin/AdminOverview';
import AdminUsers from './pages/admin/AdminUsers';
import AdminRouters from './pages/admin/AdminRouters';
import AdminTransactions from './pages/admin/AdminTransactions';
import AdminLayout from './layouts/AdminLayout';
import { SearchProvider } from './context/SearchContext';

function App() {
  return (
    <BrowserRouter>
      <SearchProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/routers" element={<Routers />} />
            <Route path="/wallet" element={<Wallet />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/support" element={<Support />} />
            <Route path="/account" element={<Account />} />
            <Route path="/hotspot" element={<Hotspot />} />
            <Route path="/hotspot/suivi" element={<HotspotMonitor />} />
            <Route element={<AdminRoute />}>
              <Route element={<AdminLayout />}>
                <Route path="/admin" element={<AdminOverview />} />
                <Route path="/admin/users" element={<AdminUsers />} />
                <Route path="/admin/routers" element={<AdminRouters />} />
                <Route path="/admin/transactions" element={<AdminTransactions />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </SearchProvider>
    </BrowserRouter>
  );
}

export default App;