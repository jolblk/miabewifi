import axios from 'axios';

function getToken() {
    return localStorage.getItem('miabewifi_token') || sessionStorage.getItem('miabewifi_token');
}

// Remplace le jeton de connexion en le gardant au même endroit (localStorage = « rester
// connecté », sessionStorage = jusqu'à la fermeture du navigateur).
export function replaceToken(token) {
    const storage = localStorage.getItem('miabewifi_token') ? localStorage : sessionStorage;
    storage.setItem('miabewifi_token', token);
}

// Vrai si la connexion actuelle a été ouverte avec « Rester connecté sur cet appareil ».
export function isRememberedSession() {
    return Boolean(localStorage.getItem('miabewifi_token'));
}

const api = axios.create({ baseURL: '' });

api.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Un 401 sur /auth/login signifie « identifiants incorrects » : on laisse
        // la page de login afficher l'erreur au lieu de recharger la page.
        const isLoginRequest = error.config?.url?.includes('/auth/login');
        if (error.response?.status === 401 && !isLoginRequest) {
            localStorage.removeItem('miabewifi_token');
            sessionStorage.removeItem('miabewifi_token');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;