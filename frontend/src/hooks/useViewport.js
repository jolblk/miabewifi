import { useState, useEffect } from 'react';

const BREAKPOINT = 768;

export function useViewport() {
    const [isMobile, setIsMobile] = useState(window.innerWidth < BREAKPOINT);

    useEffect(() => {
        const onResize = () => setIsMobile(window.innerWidth < BREAKPOINT);
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, []);

    return { isMobile };
}