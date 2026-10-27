/* Sistema da Loja — comportamentos gerais (tema, fonte, menu, máscaras pt-BR). Licença MIT. */
(function () {
  const raiz = document.documentElement;
  const guardar = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };

  // Tema, contraste e tamanho da fonte
  const ciclo = (atual, opcoes) => opcoes[(opcoes.indexOf(atual) + 1) % opcoes.length];
  document.querySelectorAll('[data-acao]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const acao = btn.dataset.acao;
      if (acao === 'tema') {
        const novo = ciclo(raiz.dataset.theme || 'auto', ['auto', 'claro', 'escuro']);
        novo === 'auto' ? raiz.removeAttribute('data-theme') : (raiz.dataset.theme = novo);
        guardar('tema', novo === 'auto' ? null : novo);
        btn.setAttribute('aria-label', 'Tema: ' + novo);
      } else if (acao === 'contraste') {
        if (raiz.dataset.contraste === 'alto') { raiz.removeAttribute('data-contraste'); guardar('contraste', null); }
        else { raiz.dataset.contraste = 'alto'; guardar('contraste', 'alto'); }
      } else if (acao === 'fonte') {
        const novo = ciclo(raiz.dataset.fonte || 'n', ['n', 'g', 'gg']);
        novo === 'n' ? raiz.removeAttribute('data-fonte') : (raiz.dataset.fonte = novo);
        guardar('fonte', novo === 'n' ? null : novo);
      } else if (acao === 'menu') {
        const aberto = document.getElementById('sidebar').classList.toggle('aberta');
        btn.setAttribute('aria-expanded', aberto);
      }
    });
  });

  // Confirmação em ações destrutivas
  document.querySelectorAll('[data-confirmar]').forEach((el) => {
    el.addEventListener('click', (ev) => { if (!confirm(el.dataset.confirmar)) ev.preventDefault(); });
  });

  // Máscaras do Brasil
  const so = (v) => v.replace(/\D/g, '');
  const mascaras = {
    telefone: (v) => { v = so(v).slice(0, 11); if (v.length > 10) return v.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3'); if (v.length > 6) return v.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3'); if (v.length > 2) return v.replace(/(\d{2})(\d{0,5})/, '($1) $2'); return v; },
    cpf: (v) => so(v).slice(0, 11).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2'),
    cnpj: (v) => so(v).slice(0, 14).replace(/(\d{2})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1/$2').replace(/(\d{4})(\d{1,2})$/, '$1-$2'),
    cep: (v) => so(v).slice(0, 8).replace(/(\d{5})(\d)/, '$1-$2'),
  };
  document.querySelectorAll('input[data-mask]').forEach((inp) => {
    const m = mascaras[inp.dataset.mask];
    if (!m) return;
    inp.value = m(inp.value);
    inp.addEventListener('input', () => { inp.value = m(inp.value); });
    if (inp.dataset.mask !== 'cep') inp.setAttribute('inputmode', 'numeric');
  });
})();

/* Busca rápida (Ctrl+K ou "/") e menu da conta */
(function () {
  const dlg = document.getElementById('busca');
  if (!dlg || typeof dlg.showModal !== 'function') return;
  const q = document.getElementById('busca-q'), lista = document.getElementById('busca-lista');
  let itens = [], sel = 0, t = null;
  const abrir = () => { if (!dlg.open) dlg.showModal(); q.value = ''; buscar(''); q.focus(); };
  const fechar = () => dlg.open && dlg.close();
  function desenhar() {
    lista.innerHTML = '';
    if (!itens.length) { const li = document.createElement('li'); li.className = 'ajuda'; li.style.padding = '.7rem 1rem'; li.textContent = 'Nada encontrado.'; lista.appendChild(li); return; }
    let grupo = '';
    itens.forEach((it, i) => {
      if (it.grupo !== grupo) { grupo = it.grupo; const h = document.createElement('li'); h.className = 'busca-grupo'; h.setAttribute('role', 'presentation'); h.textContent = grupo; lista.appendChild(h); }
      const li = document.createElement('li'); li.setAttribute('role', 'option'); li.id = 'busca-op-' + i; li.setAttribute('aria-selected', i === sel);
      li.textContent = it.rotulo; li.addEventListener('click', () => { location.href = it.url; });
      lista.appendChild(li);
    });
    q.setAttribute('aria-activedescendant', 'busca-op-' + sel);
    const ativo = document.getElementById('busca-op-' + sel); if (ativo) ativo.scrollIntoView({ block: 'nearest' });
  }
  function buscar(texto) {
    clearTimeout(t);
    t = setTimeout(() => fetch(dlg.dataset.url + '?q=' + encodeURIComponent(texto), { credentials: 'same-origin' })
      .then((r) => r.json()).then((d) => { itens = d.resultados; sel = 0; desenhar(); }).catch(() => {}), 120);
  }
  q.addEventListener('input', () => buscar(q.value.trim()));
  q.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(sel + 1, itens.length - 1); desenhar(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(sel - 1, 0); desenhar(); }
    else if (e.key === 'Enter') { e.preventDefault(); if (itens[sel]) location.href = itens[sel].url; }
    else if (e.key === 'Escape') { e.preventDefault(); fechar(); }
  });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) fechar(); });
  document.querySelectorAll('[data-acao="buscar"]').forEach((b) => b.addEventListener('click', abrir));
  document.addEventListener('keydown', (e) => {
    const digitando = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); abrir(); }
    else if (e.key === '/' && !digitando) { e.preventDefault(); abrir(); }
  });
  // fecha o menu da conta ao clicar fora
  document.addEventListener('click', (e) => { document.querySelectorAll('.menu-usuario[open]').forEach((d) => { if (!d.contains(e.target)) d.removeAttribute('open'); }); });
})();

/* Ações de produtividade em formulários */
(function () {
  document.querySelectorAll('[data-marcar-todos]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const f = document.getElementById(btn.dataset.form);
      f.querySelectorAll('input[type=radio][value="' + btn.dataset.marcarTodos + '"]').forEach((r) => { r.checked = true; });
    });
  });
  // filtros: enviam sozinhos ao mudar (menos cliques)
  document.querySelectorAll('form.filtros[data-auto]').forEach((f) => {
    let t = null;
    f.addEventListener('change', () => f.requestSubmit());
    f.querySelectorAll('input[type=search], input[type=text]').forEach((i) => i.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => f.requestSubmit(), 400); }));
  });
})();

/* Abas de formulário acessíveis (teclado: setas, Home/End). Abre a primeira aba com erro. */
(function () {
  document.querySelectorAll('[data-abas]').forEach((raiz) => {
    const abas = [...raiz.querySelectorAll('[role=tab]')], paineis = abas.map((a) => document.getElementById(a.getAttribute('aria-controls')));
    function ativar(i, foco) {
      abas.forEach((a, k) => { a.setAttribute('aria-selected', k === i); a.tabIndex = k === i ? 0 : -1; paineis[k].hidden = k !== i; });
      if (foco) abas[i].focus();
    }
    abas.forEach((a, i) => {
      a.addEventListener('click', () => ativar(i));
      a.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') { e.preventDefault(); ativar((i + 1) % abas.length, true); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); ativar((i - 1 + abas.length) % abas.length, true); }
        else if (e.key === 'Home') { e.preventDefault(); ativar(0, true); } else if (e.key === 'End') { e.preventDefault(); ativar(abas.length - 1, true); }
      });
    });
    let primeiroErro = -1;
    paineis.forEach((p, i) => { if (p.querySelector('.erro')) { abas[i].classList.add('tem-erro'); if (primeiroErro < 0) primeiroErro = i; } });
    ativar(primeiroErro >= 0 ? primeiroErro : 0);
    // mostra todos os painéis ao imprimir
    window.addEventListener('beforeprint', () => paineis.forEach((p) => { p.hidden = false; }));
  });
})();

/* Acessibilidade: regiões roláveis (tabelas largas) ficam alcançáveis pelo teclado */
(function () {
  document.querySelectorAll('.tabela-wrap, .kanban').forEach((el) => {
    if (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight) {
      if (!el.hasAttribute('tabindex')) el.tabIndex = 0;
      if (!el.getAttribute('role')) { el.setAttribute('role', 'region'); el.setAttribute('aria-label', 'Tabela rolável'); }
    }
  });
})();
