import { createContext, useContext, useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const SearchContext = createContext({ query: '', setQuery: () => { } });

export function SearchProvider({ children }) {
    const [query, setQuery] = useState('');
    const location = useLocation();

    // Vide la recherche à chaque changement de page, comme dans l'ancienne interface
    useEffect(() => {
        setQuery('');
    }, [location.pathname]);

    return (
        <SearchContext.Provider value={{ query, setQuery }}>
            {children}
        </SearchContext.Provider>
    );
}

export function useSearch() {
    return useContext(SearchContext);
}