(async function () {
  var STORAGE_KEY = 'rp_history';
  var MAX = 5;

  var container = document.getElementById('related-posts');
  if (!container) return;

  var baseurl = container.dataset.baseurl || '';
  var currentUrl = container.dataset.url;
  var currentTags = (container.dataset.tags || '').split(',').filter(Boolean);

  var history = {};
  try { history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch (e) {}
  history[currentUrl] = currentTags;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(history)); } catch (e) {}

  var posts;
  try {
    var r = await fetch(baseurl + '/posts.json');
    posts = await r.json();
  } catch (e) { return; }

  // build tag weights from every page the reader has visited
  var tagWeight = {};
  var urls = Object.keys(history);
  for (var i = 0; i < urls.length; i++) {
    var tags = history[urls[i]];
    for (var j = 0; j < tags.length; j++) {
      tagWeight[tags[j]] = (tagWeight[tags[j]] || 0) + 1;
    }
  }

  var unvisited = posts.filter(function (p) { return p.url !== currentUrl && !history[p.url]; });
  var pool = unvisited.length > 0 ? unvisited : posts.filter(function (p) { return p.url !== currentUrl; });

  var scored = pool.map(function (p) {
    var score = (p.tags || []).reduce(function (s, t) { return s + (tagWeight[t] || 0); }, 0);
    return { url: p.url, title: p.title, date: p.date, score: score };
  }).sort(function (a, b) {
    return b.score - a.score || (new Date(b.date) - new Date(a.date));
  });

  var picks = scored.slice(0, MAX);
  if (picks.length === 0) return;

  var items = picks.map(function (p) {
    return '<li><a href="' + p.url + '">' + p.title + '</a></li>';
  }).join('');

  container.innerHTML = '<h3>You might also like</h3><ul>' + items + '</ul>';
}());
