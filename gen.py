#!/usr/bin/env python3
"""Vale o Click — gera as páginas temáticas para o Google (SEO) com as ofertas do dia.

Roda no GitHub Actions a cada 6 horas (.github/workflows/paginas.yml). Lê as ofertas
da mesma fonte do site (função voc_vitrine do Supabase, chave pública) e grava:
  <slug>/index.html  — uma página por tema, com as ofertas já no HTML
  cupons/index.html  — cupons oficiais do Mercado Livre e da Shopee
  sitemap.xml, robots.txt
  index.html         — atualiza só o bloco entre <!--SEO-LINKS--> e <!--/SEO-LINKS-->
Criado em 22/10/2026.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

API = "https://pgxhfrkiitninpepppvb.supabase.co/rest/v1/rpc/voc_vitrine"
KEY = "sb_publishable_YYoQ3i_jjgpUyfz-vlfEYw_S16bBbDw"  # chave pública (a mesma do site)
SITE = "https://valeoclickofertas.com.br"
TG = "https://t.me/valeoclickofertas"
MATT = "matt_word=gprado19&matt_tool=99482770"
BR = dt.timezone(dt.timedelta(hours=-4))  # Cuiabá
OUT = os.path.dirname(os.path.abspath(__file__))

# slug, título (h1), título da aba, descrição, introdução, filtro
TEMAS = [
    ("fones-bluetooth-em-promocao", "Fones Bluetooth em promoção hoje", "Fones Bluetooth em promoção hoje | Vale o Click",
     "Fones de ouvido Bluetooth com desconto de verdade no Mercado Livre e na Shopee, preço conferido hoje.",
     "Separamos os fones de ouvido sem fio (TWS, esportivos e gamer) com o maior desconto real de hoje. Todos os preços são conferidos várias vezes por dia e só entra produto de vendedor bem avaliado.",
     lambda o: re.search(r"\b(fone|fones|headset|earbuds?|tws)\b", o["t"])),
    ("carregador-e-power-bank-em-promocao", "Carregadores e power banks em promoção", "Carregador turbo e power bank em promoção | Vale o Click",
     "Carregadores turbo, cabos e power banks com desconto, conferidos hoje no Mercado Livre e na Shopee.",
     "Carregador turbo, cabo USB-C, carregador veicular e power bank com desconto real. Bom para trocar aquele carregador lento ou ter bateria extra na bolsa.",
     lambda o: re.search(r"(carregador|power ?bank|cabo usb|cabo tipo|cabo lightning)", o["t"])),
    ("presentes-ate-50-reais", "Presentes até R$ 50 em promoção", "Presentes baratos até R$ 50 | Vale o Click",
     "Ideias de presente até R$ 50 com desconto de verdade, conferidas hoje no Mercado Livre e na Shopee.",
     "Lista de achados até R$ 50 com bom desconto: dá para presentear sem gastar muito (ou se dar um mimo). A lista muda ao longo do dia conforme as promoções.",
     lambda o: o["p"] <= 50),
    ("ofertas-ate-100-reais", "Ofertas até R$ 100", "Ofertas até R$ 100 hoje | Vale o Click",
     "Achados de até R$ 100 com desconto real no Mercado Livre e na Shopee, preço conferido hoje.",
     "Tudo até R$ 100, ordenado pelo maior desconto. São produtos dos mais vendidos, de vendedores bem avaliados, com o preço conferido hoje.",
     lambda o: o["p"] <= 100),
    ("utilidades-para-casa-em-promocao", "Utilidades para casa em promoção", "Utilidades domésticas em promoção | Vale o Click",
     "Utensílios de cozinha, potes, organizadores e utilidades para casa com desconto, conferidos hoje.",
     "Potes, organizadores, utensílios de cozinha, banheiro e lavanderia com desconto de verdade. Os achados que mais saem para deixar a casa em ordem gastando pouco.",
     lambda o: re.search(r"(cozinha|organiza|lavand|banh|casa, móveis)", o["c"]) or re.search(r"\b(potes?|organizador|lixeira|escorredor|tapete)\b", o["t"])),
    ("ofertas-pet", "Ofertas para cachorro e gato", "Produtos pet em promoção (cachorro e gato) | Vale o Click",
     "Ração, tapete higiênico, brinquedos, comedouros e acessórios pet com desconto, conferidos hoje.",
     "Achados para cachorro e gato: tapete higiênico, comedouro, brinquedos, caminhas e acessórios com desconto real.",
     lambda o: re.search(r"(pet|animai)", o["c"]) or re.search(r"\b(cachorro|cães|gato|gatos|pet)\b", o["t"])),
    ("caixa-de-som-bluetooth-em-promocao", "Caixas de som Bluetooth em promoção", "Caixa de som Bluetooth em promoção | Vale o Click",
     "Caixas de som Bluetooth com desconto, à prova d'água e potentes, conferidas hoje.",
     "Caixinhas e caixas de som Bluetooth com desconto, das portáteis à prova d'água às mais potentes para festa.",
     lambda o: re.search(r"(caixa de som|caixinha de som|speaker|soundbar)", o["t"])),
    ("informatica-em-promocao", "Informática em promoção", "Informática em promoção: mouse, teclado, notebook | Vale o Click",
     "Mouse, teclado, monitor, SSD, notebook e acessórios de informática com desconto, conferidos hoje.",
     "Periféricos e acessórios de informática com desconto real: mouse, teclado, webcam, SSD, monitor e mais.",
     lambda o: re.search(r"(informát|periféric)", o["c"]) or re.search(r"\b(mouse|teclado|notebook|monitor|webcam|ssd|pendrive|roteador)\b", o["t"])),
    ("eletrodomesticos-em-promocao", "Eletrodomésticos em promoção", "Eletrodomésticos em promoção hoje | Vale o Click",
     "Air fryer, liquidificador, cafeteira, aspirador e outros eletrodomésticos com desconto, conferidos hoje.",
     "Eletrodomésticos grandes e pequenos com desconto de verdade, de marcas conhecidas e vendedores bem avaliados.",
     lambda o: re.search(r"eletrodom", o["c"]) or re.search(r"(air ?fryer|fritadeira|liquidificador|cafeteira|aspirador|micro-?ondas|ventilador|batedeira|panela elétrica|mixer)", o["t"])),
    ("moveis-em-promocao", "Móveis em promoção", "Móveis em promoção hoje | Vale o Click",
     "Móveis, colchões e itens para o quarto e a sala com desconto, conferidos hoje no Mercado Livre.",
     "Móveis para casa, colchões, cadeiras, mesas e racks com desconto real, de vendedores bem avaliados.",
     lambda o: re.search(r"móveis|colch", o["c"]) or re.search(r"\b(cadeira|guarda-roupa|sofá|estante|rack|cômoda|colchão|escrivaninha)\b", o["t"])),
    ("ofertas-shopee", "Ofertas da Shopee hoje", "Ofertas da Shopee hoje com desconto | Vale o Click",
     "Achados da Shopee com desconto de verdade, conferidos hoje.",
     "As melhores ofertas da Shopee de hoje, com o desconto conferido. Toque no produto para comprar direto no app ou no site da Shopee.",
     lambda o: o["l"] == "shopee"),
    ("games-em-promocao", "Games em promoção", "Games em promoção: controles e acessórios | Vale o Click",
     "Controles, headsets gamer e acessórios para PS5, PS4, Xbox, Nintendo e PC com desconto, conferidos hoje.",
     "Acessórios gamer com desconto: controles, headsets, mouses e teclados gamer e mais.",
     lambda o: re.search(r"(game|console)", o["c"]) or re.search(r"\b(controle|ps5|ps4|xbox|nintendo|gamer|joystick)\b", o["t"])),
    ("eletronicos-em-promocao", "Eletrônicos em promoção", "Eletrônicos em promoção hoje | Vale o Click",
     "Eletrônicos, áudio, smartwatch e acessórios de celular com desconto, conferidos hoje.",
     "Eletrônicos com desconto real: áudio, smartwatch, câmeras, acessórios de celular e mais.",
     lambda o: re.search(r"(eletrôn|áudio|celular|câmera)", o["c"]) or re.search(r"(smartwatch|relógio inteligente|câmera|projetor|tv box)", o["t"])),
]

ESC = html.escape


def baixar():
    req = urllib.request.Request(API, data=b"{}", method="POST", headers={
        "Content-Type": "application/json", "apikey": KEY, "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def brl(v):
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def link_ok(u):
    return bool(re.match(r"^https://((www\.|produto\.)?mercadolivre\.com\.br|([a-z0-9-]+\.)?shopee\.com\.br|([a-z0-9-]+\.)?shp\.ee)/", u or ""))


def img_ok(u):
    return bool(re.match(r"^https://[a-z0-9.-]+\.(mlstatic\.com|susercontent\.com|shopee\.com\.br)/", u or ""))


def normaliza(i):
    try:
        p = float(i.get("preco") or 0)
        a = float(i.get("preco_antes") or 0)
    except (TypeError, ValueError):
        return None
    if p <= 0 or not link_ok(i.get("link")):
        return None
    off = round((1 - p / a) * 100) if a > p else 0
    return {"n": i.get("n"), "titulo": str(i.get("titulo") or "").strip(), "foto": i.get("foto") if img_ok(i.get("foto")) else "",
            "p": p, "a": a, "off": off, "link": i["link"], "frete": bool(i.get("frete_gratis")),
            "l": "shopee" if (i.get("loja") == "shopee" or "shopee" in (i.get("link") or "") or "shp.ee" in (i.get("link") or "")) else "ml",
            "t": str(i.get("titulo") or "").lower(), "c": str(i.get("categoria") or "").lower(),
            "quando": i.get("publicado_em")}


CSS = """:root{--bg:#0a0c09;--panel:#13160f;--line:#252a1e;--fg:#eef3e8;--muted:#9aa58f;--neon:#39ff14;--ink:#0a0c09;--shp:#ff6a3d;color-scheme:dark}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg)}
body{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.45;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 16px 40px}
header{display:flex;align-items:center;gap:10px;padding:4px 0 10px}header a{color:inherit;text-decoration:none;display:flex;align-items:center;gap:10px}
.mark{width:36px;height:36px;border-radius:50%;background:var(--neon);display:grid;place-items:center;flex:none}
.brand{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-weight:800;font-size:19px}
nav.crumb{font-size:13px;color:var(--muted);margin:2px 0 6px}nav.crumb a{color:var(--muted)}
h1{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-weight:800;font-size:clamp(26px,6vw,40px);line-height:1.05;margin:6px 0 8px}
.intro{color:var(--muted);max-width:680px;margin:0 0 6px}.upd{font-size:13px;color:var(--muted);margin:0 0 14px}
.tg{display:block;margin:0 0 16px;padding:12px 14px;border-radius:12px;background:var(--panel);border:1px solid var(--neon);color:var(--fg);text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
@media(min-width:640px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(min-width:900px){.grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;color:inherit;text-decoration:none;min-width:0}
.ph{position:relative;aspect-ratio:1;background:#fff}.ph img{width:100%;height:100%;object-fit:contain;display:block}
.off{position:absolute;top:8px;right:8px;background:var(--neon);color:var(--ink);font-weight:800;font-size:13px;padding:3px 8px;border-radius:99px}
.loja{position:absolute;bottom:8px;left:8px;font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;background:#fff200;color:#2d3277}.loja.shp{background:var(--shp);color:#fff}
.body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;flex:1}
.t{font-size:13.5px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;min-height:2.8em;margin:0;font-weight:500}
.price{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-weight:800;font-size:22px;line-height:1}.old{color:var(--muted);font-size:12.5px;text-decoration:line-through}
.ship{color:var(--neon);font-size:12px;font-weight:600}
.btn{margin-top:auto;background:var(--neon);color:var(--ink);text-align:center;font-weight:700;border-radius:10px;padding:10px 8px;font-size:14px}
h2{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-size:19px;margin:26px 0 10px}
.mais{display:flex;flex-wrap:wrap;gap:8px}.mais a{background:var(--panel);border:1px solid var(--line);border-radius:99px;padding:8px 13px;color:var(--fg);text-decoration:none;font-size:13.5px}
footer{margin-top:24px;color:var(--muted);font-size:12px;text-align:center;line-height:1.6}footer a{color:var(--neon)}
.cup{display:grid;gap:10px}.cup a{display:block;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;color:var(--fg);text-decoration:none}
.cup b{display:block;font-size:16px;margin-bottom:4px}.cup span{color:var(--muted);font-size:13.5px}"""

LOGO = '<svg width="22" height="22" viewBox="0 0 40 40"><path d="M7 20 15 11h17a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H15z" fill="#0a0c09"/><circle cx="16.5" cy="20" r="2.2" fill="#39ff14"/><path d="M22 14v11l2.7-2.6 2 4.4 1.9-.8-2-4.3h3.7z" fill="#39ff14"/></svg>'

HIT = """<script>
(()=>{const A="https://pgxhfrkiitninpepppvb.supabase.co/rest/v1/rpc/voc_vitrine_hit",K="%s";
const h=(n,k)=>{try{fetch(A,{method:"POST",keepalive:true,headers:{"Content-Type":"application/json",apikey:K,Authorization:"Bearer "+K},body:JSON.stringify({p_n:n,p_kind:k})})}catch(_){}};
h(0,"visita");document.addEventListener("click",e=>{const a=e.target.closest&&e.target.closest("a.card");if(a)h(Number(a.dataset.n)||0,"clique")});})();
</script>""" % KEY


def pagina(slug, h1, titulo, desc, corpo, agora, extra_head=""):
    url = f"{SITE}/{slug}/" if slug else SITE + "/"
    return f"""<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{ESC(titulo)}</title>
<meta name="description" content="{ESC(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#0a0c09">
<meta property="og:title" content="{ESC(titulo)}">
<meta property="og:description" content="{ESC(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://valeoclick.guiborestprod01.workers.dev/icon.png">
<link rel="icon" href="https://valeoclick.guiborestprod01.workers.dev/icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
{extra_head}
</head><body><div class="wrap">
<header><a href="/"><div class="mark" aria-hidden="true">{LOGO}</div><div class="brand">Vale o Click</div></a></header>
<nav class="crumb"><a href="/">Início</a> › {ESC(h1)}</nav>
<h1>{ESC(h1)}</h1>
{corpo}
<footer>#publi · Os links levam ao Mercado Livre ou à Shopee e são links de afiliado: podemos ganhar uma comissão, sem custo extra para você.<br>
Preços e estoque podem mudar a qualquer momento; confira na loja antes de comprar. Lista atualizada em {agora}.<br>
<a href="/">Todas as ofertas</a> · <a href="{TG}" rel="noopener">Telegram</a> · <a href="https://www.instagram.com/valeoclickbr.ofertas/" rel="noopener">Instagram</a> · <a href="https://x.com/ValeoClickBR" rel="noopener">X</a></footer>
</div>{HIT}</body></html>
"""


def cartao(o):
    shp = o["l"] == "shopee"
    img = f'<img src="{ESC(o["foto"])}" alt="{ESC(o["titulo"][:90])}" loading="lazy" width="300" height="300">' if o["foto"] else ""
    off = f'<span class="off">-{o["off"]}%</span>' if o["off"] >= 5 else ""
    old = f'<div class="old">{brl(o["a"])}</div>' if o["off"] >= 5 else ""
    frete = '<div class="ship">📦 Frete grátis</div>' if o["frete"] else ""
    return (f'<a class="card" data-n="{ESC(str(o["n"]))}" href="{ESC(o["link"])}" rel="noopener sponsored nofollow" target="_blank">'
            f'<div class="ph">{img}{off}<span class="loja{" shp" if shp else ""}">{"Shopee" if shp else "Mercado Livre"}</span></div>'
            f'<div class="body"><h3 class="t">{ESC(o["titulo"])}</h3><div><div class="price">{brl(o["p"])}</div>{old}</div>{frete}'
            f'<span class="btn">Ver na {"Shopee" if shp else "loja"}</span></div></a>')


def links_temas(atual, ativos):
    itens = [f'<a href="/{s}/">{ESC(h1)}</a>' for s, h1 in ativos if s != atual]
    itens.append('<a href="/cupons/">Cupons de hoje</a>' if atual != "cupons" else "")
    return '<div class="mais">' + "".join(itens) + "</div>"


def main():
    dados = baixar()
    itens = [o for o in (normaliza(i) for i in dados.get("itens", [])) if o]
    if len(itens) < 30:
        print("poucas ofertas (", len(itens), ") — não mexo nas páginas", file=sys.stderr)
        return 1
    agora = dt.datetime.now(BR).strftime("%d/%m às %H:%M")
    hoje = dt.datetime.now(BR).strftime("%Y-%m-%d")
    paginas = []
    for slug, h1, titulo, desc, intro, filtro in TEMAS:
        sel, vistos = [], set()
        for o in sorted(itens, key=lambda o: (-o["off"], o["p"])):
            k = o["t"][:40]
            if k in vistos or not filtro(o):
                continue
            vistos.add(k)
            sel.append(o)
        if len(sel) >= 4:
            paginas.append((slug, h1, titulo, desc, intro, sel[:40]))
    ativos = [(p[0], p[1]) for p in paginas]
    for slug, h1, titulo, desc, intro, sel in paginas:
        ld = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "numberOfItems": len(sel),
              "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": o["titulo"][:120], "url": o["link"]} for i, o in enumerate(sel)]}
        corpo = (f'<p class="intro">{ESC(intro)}</p><p class="upd">{len(sel)} ofertas · atualizado em {agora}</p>'
                 f'<a class="tg" href="{TG}" rel="noopener">📲 Quer receber as promoções na hora? Entre no nosso canal do Telegram →</a>'
                 f'<div class="grid">{"".join(cartao(o) for o in sel)}</div>'
                 f'<h2>Veja também</h2>{links_temas(slug, ativos)}')
        os.makedirs(os.path.join(OUT, slug), exist_ok=True)
        with open(os.path.join(OUT, slug, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina(slug, h1, titulo, desc, corpo, agora,
                           '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>"))

    # cupons oficiais (as páginas de cupom das lojas, com o nosso link de afiliado no Mercado Livre)
    cup = [
        (f"https://www.mercadolivre.com.br/cupons?{MATT}", "Cupons do Mercado Livre", "A página oficial com todos os cupons ativos do Mercado Livre. Ative o cupom antes de comprar."),
        (f"https://www.mercadolivre.com.br/ofertas?{MATT}", "Ofertas do dia do Mercado Livre", "As ofertas relâmpago e do dia, direto no Mercado Livre."),
        ("https://shopee.com.br/", "Cupons da Shopee", "Abra a Shopee e toque em \u201cCupons\u201d (no app, aba Eu) para resgatar desconto e frete grátis antes de comprar."),
    ]
    corpo = ('<p class="intro">Antes de comprar, vale ativar um cupom: muitos dão desconto extra ou frete grátis em cima das nossas ofertas. '
             'Estes são os links oficiais das lojas, sempre atualizados por elas.</p>'
             '<div class="cup">' + "".join(f'<a href="{ESC(u)}" rel="noopener sponsored nofollow" target="_blank"><b>{ESC(t)} →</b><span>{ESC(d)}</span></a>' for u, t, d in cup) + "</div>"
             f'<h2>Ofertas por tema</h2>{links_temas("cupons", ativos)}')
    os.makedirs(os.path.join(OUT, "cupons"), exist_ok=True)
    with open(os.path.join(OUT, "cupons", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina("cupons", "Cupons de desconto de hoje", "Cupons de desconto Mercado Livre e Shopee hoje | Vale o Click",
                       "Links oficiais dos cupons de desconto do Mercado Livre e da Shopee, para usar junto com as ofertas do dia.", corpo, agora))

    urls = [SITE + "/"] + [f"{SITE}/{s}/" for s, _ in ativos] + [f"{SITE}/cupons/"]
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write(f"  <url><loc>{u}</loc><lastmod>{hoje}</lastmod><changefreq>daily</changefreq></url>\n")
        f.write("</urlset>\n")
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")

    # bloco de links na página inicial
    idx = os.path.join(OUT, "index.html")
    with open(idx, encoding="utf-8") as f:
        s = f.read()
    bloco = ("<!--SEO-LINKS-->\n  <h2>Mais procurados</h2>\n  <div class=\"chips\" style=\"flex-wrap:wrap\">"
             + "".join(f'<a class="chip" style="text-decoration:none" href="/{sl}/">{ESC(h)}</a>' for sl, h in ativos)
             + '<a class="chip" style="text-decoration:none" href="/cupons/">Cupons de hoje</a></div>\n  <!--/SEO-LINKS-->')
    s2 = re.sub(r"<!--SEO-LINKS-->.*?<!--/SEO-LINKS-->", lambda m: bloco, s, flags=re.S)
    if s2 != s:
        with open(idx, "w", encoding="utf-8") as f:
            f.write(s2)
    print(f"{len(paginas)} páginas, {len(itens)} ofertas lidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
