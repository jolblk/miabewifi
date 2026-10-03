// Boîte de confirmation asynchrone : const ok = await confirmDialog('Message', { confirmLabel, danger })
let listener = null;

export function registerConfirmListener(fn) {
    listener = fn;
    return () => {
        if (listener === fn) listener = null;
    };
}

export function confirmDialog(message, options = {}) {
    if (!listener) return Promise.resolve(window.confirm(message));
    return new Promise((resolve) => listener({ message, ...options, resolve }));
}
