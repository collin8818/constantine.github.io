document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('menu-btn');
  const nav = document.getElementById('site-nav');
  if (!btn || !nav) return;

  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // Optional: close menu after tapping a link on mobile
  nav.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
      nav.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
});

<script>
  const concepts = [
    "Composite Output Gap",
    "Open-Economy Golden Rule",
    "Missing-Imports Problem"
  ];

  let index = 0;
  const conceptEl = document.getElementById("rotating-concept");

  setInterval(() => {
    conceptEl.style.opacity = 0;

    setTimeout(() => {
      index = (index + 1) % concepts.length;
      conceptEl.textContent = concepts[index];
      conceptEl.style.opacity = 1;
    }, 400);
  }, 3000);
</script>
