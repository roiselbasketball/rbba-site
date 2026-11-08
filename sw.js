/* RBBA – service worker : l'appli s'ouvre même sans réseau (dernières pages et données vues). */
importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");
const VERSION = "rbba-v10";
const SHELL = ["./", "index.html", "matchs.html", "appli.html", "mentions-legales.html", "assets/style.css", "assets/app.js", "assets/ui.js", "assets/logo.webp", "assets/icon-192.png", "manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  // Données et pages : réseau d'abord (toujours à jour), copie locale si hors ligne
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }).then((r) => r || caches.match("index.html")))
  );
});
