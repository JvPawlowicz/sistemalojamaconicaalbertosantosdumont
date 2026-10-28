/* Gera os ícones PNG do aplicativo (PWA/favicon) a partir de static/img/emblema.svg.
 * Uso: npm i --no-save playwright && node tools/gerar_icones.js */
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const raiz = path.resolve(__dirname, '..');
const svg = fs.readFileSync(path.join(raiz, 'static/img/emblema.svg'), 'utf8');
const dataUri = 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
const itens = [
  ['icon-192.png', 192, 0.8, '#d9eefa', 0.22], ['icon-512.png', 512, 0.8, '#d9eefa', 0.22],
  ['icon-maskable-512.png', 512, 0.6, '#d9eefa', 0], ['apple-touch-icon.png', 180, 0.78, '#d9eefa', 0],
  ['favicon-32.png', 32, 1, 'transparent', 0],
];
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  for (const [nome, tam, escala, fundo, raio] of itens) {
    await p.setViewportSize({ width: tam, height: tam });
    await p.setContent(`<body style="margin:0;background:transparent"><div style="width:${tam}px;height:${tam}px;background:${fundo};border-radius:${raio * 100}%;display:grid;place-items:center"><img src="${dataUri}" style="width:${tam * escala}px;height:${tam * escala}px"></div></body>`);
    await p.screenshot({ path: path.join(raiz, 'static/icons', nome), omitBackground: true });
  }
  await b.close();
})();
