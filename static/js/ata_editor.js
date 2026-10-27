/* Editor de ata: ao digitar @ abre a lista de modelos de texto; Enter/clique insere o texto no cursor. */
(function () {
  const ta = document.getElementById('ata-conteudo');
  if (!ta) return;
  const url = ta.dataset.urlModelos, sessao = ta.dataset.sessao;
  let pop = null, itens = [], sel = 0, inicio = -1, timer = null;

  function fechar() { if (pop) { pop.remove(); pop = null; } itens = []; inicio = -1; }
  function posicionar() {
    const r = ta.getBoundingClientRect();
    pop.style.left = (window.scrollX + r.left + 16) + 'px';
    pop.style.top = (window.scrollY + r.top + 40) + 'px';
  }
  function mostrar() {
    if (!pop) { pop = document.createElement('div'); pop.className = 'sugestoes'; pop.setAttribute('role', 'listbox'); pop.id = 'sugestoes-ata'; document.body.appendChild(pop); ta.setAttribute('aria-controls', pop.id); }
    pop.innerHTML = '';
    if (!itens.length) { const v = document.createElement('div'); v.className = 'ajuda'; v.style.padding = '.6rem'; v.textContent = 'Nenhum modelo encontrado.'; pop.appendChild(v); }
    itens.forEach((it, i) => {
      const o = document.createElement('div'); o.setAttribute('role', 'option'); o.setAttribute('aria-selected', i === sel);
      const t = document.createElement('strong'); t.textContent = it.titulo;
      const s = document.createElement('small'); s.textContent = '@' + it.atalho + ' · ' + it.categoria;
      o.append(t, s);
      o.addEventListener('mousedown', (e) => { e.preventDefault(); inserir(i); });
      pop.appendChild(o);
    });
    posicionar();
  }
  function inserir(i) {
    const it = itens[i]; if (!it) return;
    const fim = ta.selectionStart;
    ta.value = ta.value.slice(0, inicio) + it.texto + ta.value.slice(fim);
    const p = inicio + it.texto.length; ta.setSelectionRange(p, p); ta.focus();
    fechar();
  }
  function buscar(q) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fetch(url + '?sessao=' + encodeURIComponent(sessao) + '&q=' + encodeURIComponent(q), { credentials: 'same-origin' })
        .then((r) => r.json()).then((d) => { itens = d.itens; sel = 0; mostrar(); }).catch(() => {});
    }, 120);
  }
  ta.addEventListener('input', () => {
    const pos = ta.selectionStart, antes = ta.value.slice(0, pos);
    const m = /(^|\s)@([\wÀ-ÿ-]*)$/.exec(antes);
    if (m) { inicio = pos - m[2].length - 1; buscar(m[2]); } else { fechar(); }
  });
  ta.addEventListener('keydown', (e) => {
    if (!pop) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = (sel + 1) % Math.max(itens.length, 1); mostrar(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); sel = (sel - 1 + itens.length) % Math.max(itens.length, 1); mostrar(); }
    else if (e.key === 'Enter' || e.key === 'Tab') { if (itens.length) { e.preventDefault(); inserir(sel); } }
    else if (e.key === 'Escape') { fechar(); }
  });
  ta.addEventListener('blur', () => setTimeout(fechar, 150));
})();
