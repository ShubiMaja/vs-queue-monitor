/* Minimal service worker for reliable desktop notifications.
   This app does not use push; it only uses showNotification() when the page asks. */

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    // Any click (or the explicit "Open monitor" action) should focus/open the app.
    // The page may not be controlled yet; includeUncontrolled helps.
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      try {
        if ("focus" in c) return await c.focus();
      } catch {
        // ignore
      }
    }
    try {
      await self.clients.openWindow("./");
    } catch {
      // ignore
    }
  })());
});

