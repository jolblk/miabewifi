import axios from 'axios';

function getToken() {
    return localStorage.getItem('miabewifi_token') || sessionStorage.getItem('miabewifi_token');
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
        if (error.response?.status === 401) {
            localStorage.removeItem('miabewifi_token');
            sessionStorage.removeItem('miabewifi_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;