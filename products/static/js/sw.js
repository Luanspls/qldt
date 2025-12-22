// ===== SERVICE WORKER =====
const CACHE_NAME = 'train-program-v1';
const STATIC_ASSETS = [
    '/static/css/train_program.css',
    '/static/js/train_program.js',
    // '/static/images/',
    'https://code.jquery.com/jquery-3.6.0.min.js'
];

self.addEventListener('install', (event) => {
    //event.waitUntil(
    //    caches.open(CACHE_NAME)
    //        .then(cache => cache.addAll(STATIC_ASSETS))
    //        .then(() => self.skipWaiting())
    //);
    console.log('Service Worker: Installing...');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activated');
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip API requests
    if (event.request.url.includes('/api/')) return;

    // Bỏ qua các request không phải từ cùng origin
    if (!event.request.url.startsWith(self.location.origin)) return;
    
    event.respondWith(
        fetch(event.request)
            .catch(() => {
                // Khi offline, chỉ trả về cached content cho CSS/JS
                if (event.request.url.includes('.css') || 
                    event.request.url.includes('.js')) {
                    return caches.match(event.request);
                }
                return null;
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
