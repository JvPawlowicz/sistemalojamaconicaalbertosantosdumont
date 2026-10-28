import { build } from 'esbuild';
import { copyFileSync, mkdirSync } from 'node:fs';
await build({
  entryPoints: ['src/editor.js'], bundle: true, minify: true, format: 'iife', globalName: 'EditorAta',
  target: ['es2020'], outfile: '../../static/vendor/editor-ata.js', legalComments: 'none', logLevel: 'info',
  banner: { js: '/* Editor de atas — Tiptap 2 / ProseMirror (MIT). Fonte: tools/editor-ata. Gerado por esbuild. */' },
});
mkdirSync('../../static/vendor', { recursive: true });
copyFileSync('LICENSES-THIRD-PARTY.txt', '../../static/vendor/editor-ata.LICENSES.txt');
