// ===== SERVICE WORKER =====
const CACHE_NAME = 'train-program-v1';
const STATIC_ASSETS = [
    '/static/css/train_program.css',
    '/static/js/train_program.js',
    // '/static/images/',
    'https://code.jquery.com/jquery-3.6.0.min.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip API requests
    if (event.request.url.includes('/api/')) return;
    
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                
                return fetch(event.request).then(response => {
                    // Don't cache if not a success response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                });
            })
    );
});

// ===== INITIALIZE APP =====
let app;

document.addEventListener('DOMContentLoaded', () => {
    // Wait for critical resources
    if (document.readyState === 'complete') {
        initApp();
    } else {
        window.addEventListener('load', initApp);
    }
});

function initApp() {
    app = new App();
    app.init();
    
    // Register app for debugging
    window.app = app;
}

// Export for modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { App, AppState, ApiService };
}
