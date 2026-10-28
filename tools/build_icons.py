"""Gera static/img/icons.svg (sprite) a partir do pacote lucide-static (licença ISC).

Uso: python tools/build_icons.py /caminho/para/lucide-static/icons
"""
import re
import sys
from pathlib import Path

ICONES = """users user calendar calendar-days file-text wallet banknote shield-check book-open building-2
award clipboard-list chart-column settings log-out plus search check x pen-line mail message-circle eye
download upload landmark package scale bell menu sun moon contrast house folder user-plus map-pin qr-code
archive briefcase-business handshake inbox send printer trash-2 pencil circle-alert triangle-alert lock
key-round history baby heart-pulse graduation-cap gavel file-check clock circle-check circle-x type
chevron-right chevron-down arrow-left external-link refresh-cw layout-dashboard scroll-text stamp
id-card megaphone heart-handshake smartphone vote scan-line file-search video hand-heart ruler compass bell-ring hospital
stethoscope piggy-bank badge-check ticket sparkles""".split()


def main(origem: Path) -> None:
    saida = ["<svg xmlns=\"http://www.w3.org/2000/svg\" style=\"display:none\">",
             "<!-- Ícones: Lucide (ISC License) — https://lucide.dev -->"]
    for nome in ICONES:
        arq = origem / f"{nome}.svg"
        if not arq.exists():
            print("ausente:", nome)
            continue
        svg = arq.read_text(encoding="utf-8")
        corpo = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1).strip()
        corpo = re.sub(r"\s+", " ", corpo)
        saida.append(f'<symbol id="i-{nome}" viewBox="0 0 24 24">{corpo}</symbol>')
    saida.append("</svg>")
    destino = Path(__file__).resolve().parent.parent / "static" / "img" / "icons.svg"
    destino.write_text("\n".join(saida), encoding="utf-8")
    print("escrito", destino)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
