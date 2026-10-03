import { useState, useEffect } from 'react';

const BREAKPOINT = 768;

// Mobile = écran étroit, OU téléphone tenu en paysage (écran tactile peu haut).
function computeIsMobile() {
    const narrow = window.innerWidth < BREAKPOINT;
    const landscapePhone = window.innerHeight < 500 && window.matchMedia('(pointer: coarse)').matches;
    return narrow || landscapePhone;
}

export function useViewport() {
    const [isMobile, setIsMobile] = useState(computeIsMobile);

    useEffect(() => {
        const onResize = () => setIsMobile(computeIsMobile());
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, []);

    return { isMobile };
}