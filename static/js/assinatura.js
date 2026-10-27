/* Captura da assinatura (desenho em canvas) e da geolocalização (opcional, com consentimento do navegador). */
(function () {
  const canvas = document.getElementById('assinatura-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const campo = document.getElementById('assinatura_png');
  let desenhando = false, riscou = false;

  function ajustar() {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = r.width * dpr; canvas.height = r.height * dpr;
    ctx.scale(dpr, dpr); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.strokeStyle = '#0b1b3a';
  }
  ajustar();
  const pos = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  canvas.addEventListener('pointerdown', (e) => { desenhando = true; canvas.setPointerCapture(e.pointerId); ctx.beginPath(); ctx.moveTo(...pos(e)); });
  canvas.addEventListener('pointermove', (e) => { if (!desenhando) return; ctx.lineTo(...pos(e)); ctx.stroke(); riscou = true; });
  const fim = () => { if (!desenhando) return; desenhando = false; if (riscou) campo.value = canvas.toDataURL('image/png'); };
  canvas.addEventListener('pointerup', fim); canvas.addEventListener('pointercancel', fim);
  document.getElementById('assinatura-limpar').addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height); campo.value = ''; riscou = false;
  });

  const lat = document.getElementById('latitude'), lon = document.getElementById('longitude'), prec = document.getElementById('precisao');
  const estado = document.getElementById('geo-estado');
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (p) => { lat.value = p.coords.latitude.toFixed(6); lon.value = p.coords.longitude.toFixed(6); prec.value = Math.round(p.coords.accuracy); if (estado) estado.textContent = 'Localização registrada (precisão ~' + Math.round(p.coords.accuracy) + ' m).'; },
      () => { if (estado) estado.textContent = 'Localização não autorizada; a assinatura seguirá sem geolocalização.'; },
      { enableHighAccuracy: false, timeout: 10000 }
    );
  }
  document.getElementById('form-assinar').addEventListener('submit', (e) => {
    const foto = document.getElementById('foto_assinatura');
    if (!campo.value && !(foto && foto.files.length)) { e.preventDefault(); alert('Desenhe a assinatura ou envie uma foto dela.'); }
  });
})();
