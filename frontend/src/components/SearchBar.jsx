import { useState, useRef } from 'react';
import { Search } from 'lucide-react';
import { useSearch } from '../context/SearchContext';
import './SearchBar.css';

export default function SearchBar({ placeholder = 'Rechercher...' }) {
    const { query, setQuery } = useSearch();
    const [expanded, setExpanded] = useState(false);
    const inputRef = useRef(null);

    function handleBarClick() {
        if (window.innerWidth <= 640 && !expanded) {
            setExpanded(true);
            setTimeout(() => inputRef.current?.focus(), 0);
        }
    }

    function handleBlur() {
        if (window.innerWidth <= 640 && query.trim() === '') {
            setExpanded(false);
        }
    }

    return (
        <div className={`search-bar ${expanded ? 'expanded' : ''}`} onClick={handleBarClick}>
            <Search size={16} className="search-icon" />
            <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onBlur={handleBlur}
                placeholder={placeholder}
                aria-label="Rechercher"
            />
        </div>
    );
}