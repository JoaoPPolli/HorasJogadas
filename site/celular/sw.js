/* Only the application shell is cached. Session data never enters this cache. */
const CACHE = 'horasjogadas-companion-shell-v3.5.0-2';
const FILES = ['./', './index.html', './app.css', './app.js', './icon-192.png', './icon-512.png', './apple-touch-icon.png', './manifest.webmanifest'];
const ALLOWED = new Set(FILES.map(name => new URL(name, self.registration.scope).pathname));
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)));
  // No skipWaiting: an update cannot replace a page with a running session.
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(names => Promise.all(names.filter(name => name.startsWith('horasjogadas-companion-shell-') && name !== CACHE).map(name => caches.delete(name)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !ALLOWED.has(url.pathname)) return;
  event.respondWith(caches.open(CACHE).then(async cache => {
    const cached = await cache.match(event.request, {ignoreSearch:true});
    return cached || fetch(event.request);
  }));
});
