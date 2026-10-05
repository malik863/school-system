from django.http import HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def service_worker(request):
    source = r'''const STATIC_CACHE = "school-static-v1";
let currentUser = null;
const META_CACHE = "school-offline-meta-v1";

async function getCurrentUser() {
  if (currentUser) return currentUser;
  const cache = await caches.open(META_CACHE);
  const response = await cache.match("/offline-current-user");
  if (response) currentUser = await response.text();
  return currentUser || null;
}

self.addEventListener("install", event => {
  event.waitUntil(caches.open(STATIC_CACHE).then(cache => cache.addAll([
    "/static/js/offline-core.js",
    "/static/js/offline-attendance.js"
  ])));
  self.skipWaiting();
});

self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));

self.addEventListener("message", event => {
  if (!event.data || event.data.type !== "SET_USER") return;
  const next = String(event.data.userId || "");
  currentUser = next || null;
  // Persist identity so cached pages still work after a browser restart while offline.
  event.waitUntil((async () => {
    const meta = await caches.open(META_CACHE);
    await meta.put("/offline-current-user", new Response(next));
    const keys = await caches.keys();
    await Promise.all(keys.map(key => {
      if (key.startsWith("school-pages-") && key !== `school-pages-${next}`) return caches.delete(key);
    }));
  })());
});

function isCacheablePage(request) {
  if (request.method !== "GET" || request.mode !== "navigate") return false;
  const url = new URL(request.url);
  return url.origin === self.location.origin && (url.pathname.startsWith("/teacher/") || url.pathname.startsWith("/manager/"));
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  if (isCacheablePage(request)) {
    event.respondWith((async () => {
      const user = await getCurrentUser();
      const cacheName = user ? `school-pages-${user}` : null;
      try {
        const response = await fetch(request);
        if (cacheName && response.ok) {
          const cache = await caches.open(cacheName);
          await cache.put(request, response.clone());
        }
        return response;
      } catch (_) {
        if (cacheName) {
          const cached = await caches.match(request, {cacheName});
          if (cached) return cached;
        }
        return new Response("لا توجد نسخة محفوظة من هذه الصفحة على الجهاز.", {status: 503, headers: {"Content-Type": "text/plain; charset=utf-8"}});
      }
    })());
    return;
  }

  const url = new URL(request.url);
  if (url.pathname.startsWith("/static/") || url.origin !== self.location.origin) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      const copy = response.clone();
      caches.open(STATIC_CACHE).then(cache => cache.put(request, copy)).catch(() => {});
      return response;
    })));
  }
});'''
    response = HttpResponse(source, content_type="application/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    return response
