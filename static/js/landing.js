/* Landing: revelação ao rolar, barra de progresso, 3D que acompanha o ponteiro, contadores. Respeita prefers-reduced-motion. */
(function () {
  const reduz = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const topo = document.getElementById('topo'), barra = document.getElementById('progresso-barra');
  function aoRolar() {
    const y = window.scrollY, h = document.documentElement.scrollHeight - window.innerHeight;
    if (barra) barra.style.width = (h > 0 ? (y / h) * 100 : 0) + '%';
    if (topo) topo.classList.toggle('fixo', y > 24);
  }
  window.addEventListener('scroll', aoRolar, { passive: true }); aoRolar();

  // Revelação ao rolar
  const alvos = document.querySelectorAll('[data-revelar]');
  if (!('IntersectionObserver' in window) || reduz) { alvos.forEach((a) => a.classList.add('visivel')); }
  else {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('visivel'); io.unobserve(e.target); } }), { threshold: 0.15, rootMargin: '0px 0px -6% 0px' });
    alvos.forEach((a) => io.observe(a));
  }

  // Contadores
  document.querySelectorAll('[data-contar]').forEach((el) => {
    const fim = parseInt(el.dataset.contar, 10), suf = el.dataset.sufixo || '';
    if (reduz) { el.textContent = fim + suf; return; }
    const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) { io.disconnect(); const t0 = performance.now();
      (function passo(t) { const p = Math.min((t - t0) / 1400, 1); el.textContent = Math.round(fim * (1 - Math.pow(1 - p, 3))) + suf; if (p < 1) requestAnimationFrame(passo); })(t0); } }, { threshold: 0.6 });
    io.observe(el);
  });

  // Passos: destaca o passo visível
  const passos = document.querySelectorAll('[data-passo]');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => e.target.classList.toggle('ativo', e.isIntersecting)), { rootMargin: '-40% 0px -40% 0px' });
    passos.forEach((p) => io.observe(p));
  }

  // 3D: a cena e os cartões acompanham o ponteiro
  if (!reduz && window.matchMedia('(hover: hover)').matches) {
    const cena = document.getElementById('cena');
    if (cena) {
      const hero = cena.closest('.hero');
      hero.addEventListener('pointermove', (e) => { const r = hero.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        cena.style.setProperty('--ry', (x * 22) + 'deg'); cena.style.setProperty('--rx', (-y * 16) + 'deg'); });
      hero.addEventListener('pointerleave', () => { cena.style.setProperty('--ry', '0deg'); cena.style.setProperty('--rx', '0deg'); });
    }
    document.querySelectorAll('[data-tilt]').forEach((el) => {
      const base = el.classList.contains('ata-folha') ? [6, -10] : [0, 0];
      el.addEventListener('pointermove', (e) => { const r = el.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        el.style.setProperty('--ry', (base[1] + x * 14) + 'deg'); el.style.setProperty('--rx', (base[0] - y * 14) + 'deg'); });
      el.addEventListener('pointerleave', () => { el.style.setProperty('--ry', base[1] + 'deg'); el.style.setProperty('--rx', base[0] + 'deg'); });
    });
  }
  // desenho da assinatura quando a figura aparece
  const demo = document.querySelector('.ata-demo');
  if (demo && !reduz && 'IntersectionObserver' in window) { const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) { demo.classList.add('visivel'); io.disconnect(); } }, { threshold: 0.4 }); io.observe(demo); }
  else if (demo) demo.classList.add('visivel');
})();
