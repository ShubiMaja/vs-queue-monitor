self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", function (event) {
  var data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_err) {
    try {
      data = { body: event.data ? event.data.text() : "" };
    } catch (_err2) {
      data = {};
    }
  }
  var kind = data && data.kind ? String(data.kind) : "";
  var icon = data && data.icon ? data.icon : (kind === "completion" ? "/notify-completion.svg" : kind === "failure" ? "/notify-failure.svg" : kind === "warning" ? "/notify-warning.svg" : "/notify-icon.svg");
  var options = {
    body: data && data.body ? String(data.body) : "",
    icon: icon,
    badge: data && data.badge ? data.badge : icon,
    tag: data && data.tag ? String(data.tag) : "vsqm-push",
    renotify: !!(data && data.renotify),
    data: {
      url: data && data.url ? String(data.url) : "/",
    },
  };
  event.waitUntil(
    self.registration.showNotification(
      data && data.title ? String(data.title) : "VS Queue Monitor",
      options
    )
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var targetUrl = "/";
  if (event.notification && event.notification.data && event.notification.data.url) {
    targetUrl = event.notification.data.url;
  }
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clients) {
      var i;
      for (i = 0; i < clients.length; i++) {
        var client = clients[i];
        if (!client) continue;
        if ("focus" in client) {
          if ("navigate" in client) {
            try {
              client.navigate(targetUrl);
            } catch (_err) {}
          }
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return null;
    })
  );
});
