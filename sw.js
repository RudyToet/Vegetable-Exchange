const CACHE = "vpt-v3";
const ASSETS = [
  "./", "./index.html", "./manifest.json",
  "./logo.png", "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png",
  "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = e.request.url;
  // Live data: always try network first, fall back to cache
  if (url.includes("prices.json") || url.includes("open-meteo") || url.includes("api.github")) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  // App shell: cache first, then network
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
