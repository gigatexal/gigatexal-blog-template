const list = document.getElementById('tags-list');
[...list.querySelectorAll('li')]
  .sort((a, b) => +b.dataset.count - +a.dataset.count)
  .forEach(li => list.appendChild(li));

function applyTag(tag) {
  document.querySelector('.tag-link.active')?.classList.remove('active');
  const link = list.querySelector(`.tag-link[data-tag="${tag}"]`);
  if (link) link.classList.add('active');
  document.querySelectorAll('.month-posts li').forEach(li => {
    const tags = li.dataset.tags ? li.dataset.tags.split(',') : [];
    li.classList.toggle('hidden', !tags.includes(tag));
  });
  document.querySelectorAll('.month-group').forEach(g => {
    const hasVisible = g.querySelectorAll('.month-posts li:not(.hidden)').length > 0;
    g.classList.toggle('empty', !hasVisible);
  });
}

function clearTag() {
  document.querySelector('.tag-link.active')?.classList.remove('active');
  document.querySelectorAll('.month-posts li').forEach(li => li.classList.remove('hidden'));
  document.querySelectorAll('.month-group').forEach(g => g.classList.remove('empty'));
}

const urlTag = new URLSearchParams(location.search).get('tag');
if (urlTag) applyTag(urlTag);

let active = urlTag || null;
list.addEventListener('click', e => {
  const link = e.target.closest('.tag-link');
  if (!link) return;
  e.preventDefault();
  const tag = link.dataset.tag;

  if (active === tag) {
    active = null;
    clearTag();
    history.replaceState(null, '', location.pathname);
  } else {
    active = tag;
    applyTag(tag);
    history.replaceState(null, '', `?tag=${tag}`);
  }
});
