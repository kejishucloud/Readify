/* Offline static-shell cache ONLY. Authenticated book content is never cached. */
const CACHE="readify-v2-static-1";
const PATHS=["/static/css/reader-v2.css","/static/js/reader-v2.js"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(PATHS)));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==self.location.origin||!PATHS.includes(u.pathname))return;
  e.respondWith(caches.match(e.request).then(hit=>hit||fetch(e.request)));
});