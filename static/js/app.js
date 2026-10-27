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
