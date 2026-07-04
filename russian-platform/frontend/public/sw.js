/* Service worker: offline-first caching.
 *
 * Static assets: cache-first (hashed filenames make staleness impossible).
 * GET /api/*: network-first with cache fallback, so lessons, dictionary,
 * grammar, texts, and practice plans remain readable offline.
 * Non-GET requests pass through untouched — the app layer queues review
 * writes itself (src/lib/offline.ts).
 */
const STATIC_CACHE = 'rli-static-v1';
const API_CACHE = 'rli-api-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(['/', '/index.html'])),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => ![STATIC_CACHE, API_CACHE].includes(key))
          .map((key) => caches.delete(key)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  if (url.pathname.startsWith('/api/')) {
    // Network-first: fresh when online, cached content offline.
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(API_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match(request).then((hit) => hit ?? Response.error())),
    );
    return;
  }

  // Static: cache-first with background fill.
  event.respondWith(
    caches.match(request).then(
      (hit) =>
        hit ??
        fetch(request).then((response) => {
          if (response.ok && url.origin === location.origin) {
            const copy = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        }),
    ),
  );
});
