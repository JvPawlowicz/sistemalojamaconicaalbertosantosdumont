/* Auditoria de acessibilidade automatizada (axe-core: WCAG 2.0/2.1/2.2 A e AA + boas práticas).
 *
 * Uso (com o servidor de desenvolvimento rodando e os dados de `seed_inicial --demo`):
 *   npm i --no-save playwright axe-core
 *   BASE=http://127.0.0.1:8000 node tools/a11y_audit.js
 * Audita as principais telas nos temas claro, escuro e alto contraste. Sai com código 1 se houver violações.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const axeSrc = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const base = process.env.BASE || 'http://127.0.0.1:8000';
const usuario = process.env.USUARIO || 'veneravel', senha = process.env.SENHA || 'demo-senha-123';
const paginas = ['/entrar/', '/', '/sessoes/agenda/', '/sessoes/', '/sessoes/1/', '/sessoes/1/?aba=escala', '/sessoes/1/?aba=presenca',
  '/sessoes/1/?aba=visitantes', '/sessoes/1/?aba=cerimonias', '/irmaos/', '/irmaos/novo/', '/irmaos/1/', '/cargos/', '/atas/', '/atas/1/',
  '/tesouraria/', '/tesouraria/mensalidades/', '/tesouraria/caixa/', '/tesouraria/orcamento/', '/relatorios/', '/relatorios/frequencia/',
  '/documentos/', '/candidatos/', '/patrimonio/', '/expediente/', '/comissoes/', '/configuracoes/', '/meus-dados/', '/irmaos/meu-perfil/',
  '/visitas/', '/sessoes/eventos/', '/atas/modelos/', '/agape/', '/agape/caixa/', '/agape/inventario/', '/votacoes/', '/hospitalaria/', '/hospitalaria/tronco/', '/irmaos/carteirinha/', '/avisos/'];
const modos = [['claro', {}], ['escuro', { theme: 'escuro' }], ['contraste', { contraste: 'alto' }]];
(async () => {
  const b = await chromium.launch(); const falhas = [];
  for (const [nome, cfg] of modos) {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage();
    for (const pub of ['/', '/entrar/']) { if (nome !== 'claro' && pub === '/entrar/') continue; const rp = await p.goto(base + pub); await p.evaluate((c) => { if (c.theme) document.documentElement.dataset.theme = c.theme; if (c.contraste) document.documentElement.dataset.contraste = c.contraste; }, cfg); await p.waitForTimeout(1500); await p.evaluate(axeSrc); const vp = await p.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] } })).violations.map((x) => `${x.id} [${x.impact}] ${x.nodes[0].target.join(' ').slice(0, 80)}`)); vp.forEach((x) => falhas.push(`${nome} (público) ${pub}: ${x}`)); }
    await p.goto(base + '/entrar/'); await p.fill('#id_username', usuario); await p.fill('#id_password', senha);
    await p.click('form button:has-text("Entrar")'); await p.waitForLoadState();
    if (p.url().includes('aceite-termo')) { await p.check('#aceito'); await p.click('text=Aceitar e continuar'); await p.waitForLoadState(); }
    for (const pg of paginas) {
      if (pg === '/entrar/' && nome !== 'claro') continue;
      const r = await p.goto(base + pg); if (!r || r.status() >= 400) { falhas.push(`${nome} ${pg}: HTTP ${r && r.status()}`); continue; }
      await p.evaluate((c) => { if (c.theme) document.documentElement.dataset.theme = c.theme; if (c.contraste) document.documentElement.dataset.contraste = c.contraste; }, cfg);
      await p.waitForTimeout(900); // espera as animações de entrada terminarem
      await p.evaluate(axeSrc);
      const v = await p.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] } })).violations.map((x) => `${x.id} [${x.impact}] ${x.nodes[0].target.join(' ').slice(0, 80)}`));
      v.forEach((x) => falhas.push(`${nome} ${pg}: ${x}`));
    }
    await ctx.close();
  }
  await b.close();
  console.log(falhas.length ? falhas.join('\n') : `OK: ${paginas.length} telas × ${modos.length} temas sem violações.`);
  process.exit(falhas.length ? 1 : 0);
})();
