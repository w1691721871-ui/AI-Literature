const CACHE_NAME = "researchos-workspace-v152";
// Keep navigation documents network-first. Caching index.html would preserve
// an old script URL across releases even when the shell cache version changes.
const APP_SHELL = ["./styles.css?v=152", "./runtime-config.js?v=1", "./app.js?v=152", "./manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names
        .filter((name) => (name.startsWith("ai-insight-agent-shell-") || name.startsWith("ai-research-workspace-") || name.startsWith("researchos-workspace-")) && name !== CACHE_NAME)
        .map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
