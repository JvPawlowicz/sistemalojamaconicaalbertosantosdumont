/* Editor de atas — Tiptap (ProseMirror, MIT). Empacotado como window.EditorAta.init(opcoes). */
import { Editor, Extension } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import Suggestion from '@tiptap/suggestion';

const ESTRUTURA = [
  ['Cabeçalho', 'Sessão {{tipo}} de {{grau}} da {{loja}}, realizada em {{data_extenso}}.'],
  ['Abertura dos trabalhos', ''],
  ['Leitura e aprovação da ata anterior', ''],
  ['Expediente', ''],
  ['Ordem do dia', ''],
  ['Palavra a bem da Ordem, do quadro e da Loja', ''],
  ['Tronco de Beneficência', ''],
  ['Encerramento', ''],
];

const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const paragrafos = (texto) => String(texto).split(/\n{2,}/).map((p) => '<p>' + esc(p).replace(/\n/g, '<br>') + '</p>').join('');

function menuSugestao(editor, cfg) {
  let pop = null, itens = [], sel = 0, props = null;
  const fechar = () => { if (pop) { pop.remove(); pop = null; } };
  const desenhar = () => {
    if (!pop) { pop = document.createElement('div'); pop.className = 'sugestoes'; pop.setAttribute('role', 'listbox'); pop.id = 'sugestoes-ata'; document.body.appendChild(pop); }
    pop.innerHTML = '';
    if (!itens.length) { const v = document.createElement('div'); v.className = 'ajuda'; v.style.padding = '.6rem'; v.textContent = 'Nada encontrado.'; pop.appendChild(v); }
    let grupo = '';
    itens.forEach((it, i) => {
      if (it.grupo !== grupo) { grupo = it.grupo; const h = document.createElement('div'); h.className = 'busca-grupo'; h.textContent = grupo; pop.appendChild(h); }
      const o = document.createElement('div'); o.setAttribute('role', 'option'); o.setAttribute('aria-selected', i === sel);
      const t = document.createElement('strong'); t.textContent = it.titulo; const s = document.createElement('small'); s.textContent = it.detalhe || '';
      o.append(t, s); o.addEventListener('mousedown', (e) => { e.preventDefault(); props.command(it); }); pop.appendChild(o);
    });
    const r = props.clientRect && props.clientRect();
    if (r) { pop.style.left = (window.scrollX + r.left) + 'px'; pop.style.top = (window.scrollY + r.bottom + 6) + 'px'; }
  };
  return {
    onStart: (p) => { props = p; itens = p.items; sel = 0; desenhar(); },
    onUpdate: (p) => { props = p; itens = p.items; sel = Math.min(sel, Math.max(itens.length - 1, 0)); desenhar(); },
    onKeyDown: ({ event }) => {
      if (!pop) return false;
      if (event.key === 'ArrowDown') { sel = (sel + 1) % Math.max(itens.length, 1); desenhar(); return true; }
      if (event.key === 'ArrowUp') { sel = (sel - 1 + itens.length) % Math.max(itens.length, 1); desenhar(); return true; }
      if (event.key === 'Enter' || event.key === 'Tab') { if (itens[sel]) { props.command(itens[sel]); return true; } }
      if (event.key === 'Escape') { fechar(); return true; }
      return false;
    },
    onExit: fechar,
  };
}

function extensaoArroba(cfg) {
  return Extension.create({
    name: 'insercaoRapida',
    addProseMirrorPlugins() {
      return [Suggestion({
        editor: this.editor, char: '@', allowSpaces: false,
        items: async ({ query }) => {
          try {
            const r = await fetch(cfg.urlBusca + '?sessao=' + encodeURIComponent(cfg.sessao) + '&q=' + encodeURIComponent(query), { credentials: 'same-origin' });
            return (await r.json()).itens;
          } catch (e) { return []; }
        },
        command: ({ editor, range, props: it }) => {
          const html = it.tipo === 'irmao' ? esc(it.texto) : paragrafos(it.texto);
          editor.chain().focus().insertContentAt(range, html).run();
        },
        render: () => menuSugestao(this.editor, cfg),
      })];
    },
  });
}

function botao(rotulo, titulo, acao, ativo) {
  const b = document.createElement('button'); b.type = 'button'; b.className = 'ed-btn'; b.innerHTML = rotulo; b.title = titulo; b.setAttribute('aria-label', titulo);
  b.addEventListener('click', (e) => { e.preventDefault(); acao(); }); b.dataset.ativo = ''; b._ativo = ativo; return b;
}

export function init(cfg) {
  const raiz = document.getElementById(cfg.raiz), campo = document.getElementById(cfg.campo);
  raiz.classList.add('editor-ata');
  const barra = document.createElement('div'); barra.className = 'ed-barra'; barra.setAttribute('role', 'toolbar'); barra.setAttribute('aria-label', 'Formatação da ata');
  const corpo = document.createElement('div'); corpo.className = 'ed-corpo';
  const lateral = document.createElement('aside'); lateral.className = 'ed-lateral'; lateral.setAttribute('aria-label', 'Estrutura da ata');
  const area = document.createElement('div'); area.className = 'ed-area';
  const rodape = document.createElement('div'); rodape.className = 'ed-rodape';
  corpo.append(area, lateral); raiz.append(barra, corpo, rodape);

  const editor = new Editor({
    element: area,
    extensions: [
      StarterKit.configure({ heading: { levels: [2, 3] }, code: false, codeBlock: false, strike: false }),
      Underline, TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Placeholder.configure({ placeholder: 'Digite a ata. Use @ para inserir textos prontos ou nomes de irmãos…' }),
      CharacterCount, extensaoArroba(cfg),
    ],
    content: campo.value || '',
    editorProps: { attributes: { class: 'ed-texto', role: 'textbox', 'aria-multiline': 'true', 'aria-label': 'Texto da ata', spellcheck: 'true', lang: 'pt-BR' } },
    onUpdate: () => { sincronizar(); },
    onSelectionUpdate: () => atualizarBotoes(), onTransaction: () => atualizarBotoes(),
  });

  const btns = [];
  const add = (b) => { btns.push(b); barra.appendChild(b); return b; };
  const sep = () => { const s = document.createElement('span'); s.className = 'ed-sep'; s.setAttribute('role', 'separator'); barra.appendChild(s); };
  const ch = () => editor.chain().focus();
  const sel = document.createElement('select'); sel.className = 'ed-sel input'; sel.setAttribute('aria-label', 'Estilo do parágrafo');
  [['p', 'Parágrafo'], ['2', 'Título de seção'], ['3', 'Subtítulo']].forEach(([v, n]) => { const o = document.createElement('option'); o.value = v; o.textContent = n; sel.appendChild(o); });
  sel.addEventListener('change', () => { sel.value === 'p' ? ch().setParagraph().run() : ch().setHeading({ level: parseInt(sel.value, 10) }).run(); });
  barra.appendChild(sel); sep();
  add(botao('<b>N</b>', 'Negrito (Ctrl+B)', () => ch().toggleBold().run(), () => editor.isActive('bold')));
  add(botao('<i>I</i>', 'Itálico (Ctrl+I)', () => ch().toggleItalic().run(), () => editor.isActive('italic')));
  add(botao('<u>S</u>', 'Sublinhado (Ctrl+U)', () => ch().toggleUnderline().run(), () => editor.isActive('underline'))); sep();
  [['left', '⇤', 'Alinhar à esquerda'], ['center', '↔', 'Centralizar'], ['justify', '☰', 'Justificar'], ['right', '⇥', 'Alinhar à direita']].forEach(([a, r, t]) => add(botao(r, t, () => ch().setTextAlign(a).run(), () => editor.isActive({ textAlign: a })))); sep();
  add(botao('•', 'Lista com marcadores', () => ch().toggleBulletList().run(), () => editor.isActive('bulletList')));
  add(botao('1.', 'Lista numerada', () => ch().toggleOrderedList().run(), () => editor.isActive('orderedList')));
  add(botao('❝', 'Citação', () => ch().toggleBlockquote().run(), () => editor.isActive('blockquote')));
  add(botao('―', 'Linha separadora', () => ch().setHorizontalRule().run(), () => false)); sep();
  add(botao('↶', 'Desfazer (Ctrl+Z)', () => ch().undo().run(), () => false));
  add(botao('↷', 'Refazer (Ctrl+Y)', () => ch().redo().run(), () => false)); sep();

  // Estrutura da ata (seções-padrão)
  const est = document.createElement('select'); est.className = 'ed-sel input'; est.setAttribute('aria-label', 'Inserir seção da ata');
  const o0 = document.createElement('option'); o0.value = ''; o0.textContent = '+ Inserir seção…'; est.appendChild(o0);
  ESTRUTURA.forEach(([n], i) => { const o = document.createElement('option'); o.value = i; o.textContent = n; est.appendChild(o); });
  est.addEventListener('change', async () => {
    if (est.value === '') return; const [nome, base] = ESTRUTURA[parseInt(est.value, 10)]; est.value = '';
    let texto = base; if (base && cfg.urlRender) { try { const r = await fetch(cfg.urlRender + '?sessao=' + cfg.sessao + '&texto=' + encodeURIComponent(base), { credentials: 'same-origin' }); texto = (await r.json()).texto; } catch (e) {} }
    ch().insertContent('<h3>' + esc(nome) + '</h3>' + (texto ? '<p>' + esc(texto) + '</p>' : '<p></p>')).run();
  });
  barra.appendChild(est);
  add(botao('@', 'Inserir texto pronto ou nome de irmão', () => { ch().insertContent('@').run(); }, () => false));

  // Ditado (Web Speech API, pt-BR)
  const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition; let rec = null;
  if (Reconhecimento) {
    const bd = add(botao('🎤', 'Ditar (reconhecimento de voz em português)', () => {
      if (rec) { rec.stop(); return; }
      rec = new Reconhecimento(); rec.lang = 'pt-BR'; rec.continuous = true; rec.interimResults = false;
      rec.onresult = (e) => { for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) ch().insertContent(esc(e.results[i][0].transcript.trim()) + ' ').run(); };
      rec.onend = () => { rec = null; bd.classList.remove('ativo'); bd.setAttribute('aria-pressed', 'false'); status('Ditado encerrado.'); };
      rec.start(); bd.classList.add('ativo'); bd.setAttribute('aria-pressed', 'true'); status('Ouvindo… fale normalmente; clique no microfone para parar.');
    }, () => !!rec));
  }
  add(botao('⛶', 'Tela cheia (foco)', () => { raiz.classList.toggle('ed-cheia'); document.body.classList.toggle('ed-sem-rolagem', raiz.classList.contains('ed-cheia')); editor.commands.focus(); }, () => raiz.classList.contains('ed-cheia')));

  function atualizarBotoes() {
    btns.forEach((b) => { const a = b._ativo(); b.classList.toggle('ativo', a); b.setAttribute('aria-pressed', a ? 'true' : 'false'); });
    const h = [2, 3].find((n) => editor.isActive('heading', { level: n })); sel.value = h ? String(h) : 'p';
  }

  // Contadores, status e estrutura lateral
  const st = document.createElement('span'); st.className = 'ed-status'; st.setAttribute('role', 'status'); st.setAttribute('aria-live', 'polite');
  const cont = document.createElement('span'); cont.className = 'ed-cont'; rodape.append(cont, st);
  function status(t) { st.textContent = t; }
  function desenharLateral() {
    lateral.innerHTML = '<strong>Estrutura</strong>'; const ul = document.createElement('ul');
    editor.state.doc.descendants((no, pos) => { if (no.type.name === 'heading') { const li = document.createElement('li'); li.className = 'n' + no.attrs.level; const a = document.createElement('button'); a.type = 'button'; a.textContent = no.textContent || '(sem título)';
      a.addEventListener('click', () => { editor.chain().focus().setTextSelection(pos + 1).scrollIntoView().run(); }); li.appendChild(a); ul.appendChild(li); } });
    if (!ul.children.length) { const p = document.createElement('p'); p.className = 'ajuda'; p.textContent = 'Use "Inserir seção" para estruturar a ata.'; lateral.appendChild(p); } else lateral.appendChild(ul);
  }
  const chaveLocal = 'ata-rascunho-' + (cfg.chave || cfg.sessao);
  let salvarTimer = null;
  function sincronizar() {
    campo.value = editor.isEmpty ? '' : editor.getHTML();
    const c = editor.storage.characterCount; cont.textContent = c.words() + ' palavras · ' + c.characters() + ' caracteres';
    desenharLateral(); clearTimeout(salvarTimer);
    salvarTimer = setTimeout(() => { try { localStorage.setItem(chaveLocal, JSON.stringify({ html: campo.value, em: Date.now() })); status('Rascunho guardado neste computador às ' + new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) + '.'); } catch (e) {} }, 1500);
  }
  sincronizar(); atualizarBotoes();

  // Recuperação de rascunho local mais novo que o do servidor
  try {
    const guardado = JSON.parse(localStorage.getItem(chaveLocal) || 'null');
    if (guardado && guardado.html && guardado.html !== campo.value && guardado.em > (cfg.salvoEm || 0) * 1000) {
      const av = document.createElement('div'); av.className = 'alerta alerta-info'; av.setAttribute('role', 'alert');
      av.innerHTML = '<span>Há um rascunho mais recente guardado neste computador (' + new Date(guardado.em).toLocaleString('pt-BR') + ').</span>';
      const r = document.createElement('button'); r.type = 'button'; r.className = 'btn btn-peq'; r.textContent = 'Recuperar';
      r.addEventListener('click', () => { editor.commands.setContent(guardado.html, true); av.remove(); });
      const d = document.createElement('button'); d.type = 'button'; d.className = 'btn btn-sec btn-peq'; d.textContent = 'Descartar';
      d.addEventListener('click', () => { localStorage.removeItem(chaveLocal); av.remove(); });
      av.append(r, d); raiz.prepend(av);
    }
  } catch (e) {}
  const form = campo.closest('form'); if (form) form.addEventListener('submit', () => { sincronizar(); try { localStorage.removeItem(chaveLocal); } catch (e) {} });
  window.addEventListener('beforeunload', (e) => { if (!form || form.dataset.salvando) return; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && raiz.classList.contains('ed-cheia')) { raiz.classList.remove('ed-cheia'); document.body.classList.remove('ed-sem-rolagem'); } });
  return editor;
}
