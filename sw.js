self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
  // Laisse passer les requêtes directement vers le serveur Render
});