"""
Atualiza a seção de projetos do README com os 3 repositórios mais recentes.

Fluxo:
  1. Busca na API do GitHub os repositórios do usuário, ordenados pelo último push.
  2. Filtra: ignora forks, arquivados, o próprio repo do perfil, repos sem
     descrição ("About") e repos marcados com o tópico "ocultar-perfil".
  3. Desenha um card SVG para cada projeto (no mesmo tema escuro + ciano do
     perfil) e salva em cards/projeto-N.svg.
  4. Substitui o que estiver entre os marcadores PROJETOS:INICIO e PROJETOS:FIM
     por imagens clicáveis apontando para esses cards.

Sem dependências externas: só a biblioteca padrão do Python.
"""

import glob
import html
import json
import os
import re
import textwrap
import urllib.request
from datetime import datetime

# ---------------------------------------------------------------- configuração
USUARIO = os.environ.get("GITHUB_USER", "Scaglia05")
TOKEN = os.environ.get("GITHUB_TOKEN")      # opcional localmente, a Action fornece
QUANTIDADE = 3                              # quantos projetos mostrar
TOPICO_OCULTAR = "ocultar-perfil"           # adicione esse tópico a um repo para escondê-lo
README = "README.md"
PASTA_CARDS = "cards"
INICIO = "<!-- PROJETOS:INICIO -->"
FIM = "<!-- PROJETOS:FIM -->"

# ---------------------------------------------------------------- tema visual
# Mesmas cores do resto do README (fundo do GitHub dark + ciano 08D9D6)
COR_FUNDO = "#0d1117"
COR_BORDA = "#30363d"
COR_DESTAQUE = "#08D9D6"
COR_TEXTO = "#c9d1d9"
COR_APAGADO = "#8b949e"
FONTE = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

# Cores oficiais das linguagens no GitHub (as bolinhas da página do repo)
CORES_LINGUAGEM = {
    "C#": "#178600", "Python": "#3572A5", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HTML": "#e34c26", "CSS": "#563d7c",
    "C++": "#f34b7d", "C": "#555555", "Jupyter Notebook": "#DA5B0B",
}

# Tamanho de cada card, em pixels
LARGURA, ALTURA = 300, 170


# ================================================================ API do GitHub
def buscar_repos():
    """Pede à API os repositórios do usuário, do push mais recente para o mais antigo."""
    url = (f"https://api.github.com/users/{USUARIO}/repos"
           "?type=owner&sort=pushed&direction=desc&per_page=100")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": USUARIO,              # a API exige um User-Agent
    })
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as resposta:
        return json.load(resposta)


def filtrar(repos):
    """Fica só com os repos que fazem sentido aparecer no perfil."""
    selecionados = []
    for repo in repos:
        if repo["fork"] or repo["archived"]:
            continue
        if repo["name"].lower() == USUARIO.lower():     # o próprio repo do README
            continue
        if not repo.get("description"):                 # sem About, sem card
            continue
        if TOPICO_OCULTAR in repo.get("topics", []):
            continue
        selecionados.append(repo)
    return selecionados[:QUANTIDADE]


# ================================================================ desenho do card
def esc(texto):
    """Escapa texto para dentro do SVG (que é XML)."""
    return html.escape(texto, quote=True)


def cortar(texto, limite):
    """Corta um texto longo e coloca reticências."""
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def gerar_svg(repo, indice):
    """Desenha o card de um projeto e devolve o SVG como string."""
    nome = cortar(repo["name"], 28)
    linguagem = repo.get("language") or ""
    data = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")

    # --- descrição: quebra em até 3 linhas de ~40 caracteres
    linhas = textwrap.wrap(repo["description"], width=40)
    if len(linhas) > 3:
        linhas = linhas[:3]
        linhas[2] = cortar(linhas[2] + " ", 39) if len(linhas[2]) >= 39 else linhas[2] + "…"
    descricao = "".join(
        f'<text x="20" y="{66 + i * 18}" class="desc">{esc(l)}</text>'
        for i, l in enumerate(linhas)
    )

    # --- tópicos: "pílulas" lado a lado, enquanto couberem na largura do card
    pilulas, x = [], 20
    for topico in repo.get("topics", []):
        if topico == TOPICO_OCULTAR:
            continue
        largura = len(topico) * 6.2 + 16          # largura aproximada do texto
        if x + largura > LARGURA - 20:
            break
        pilulas.append(
            f'<rect x="{x}" y="117" width="{largura:.0f}" height="18" rx="9" class="pilula"/>'
            f'<text x="{x + largura / 2:.0f}" y="130" class="topico">{esc(topico)}</text>'
        )
        x += largura + 6

    # --- rodapé: bolinha da linguagem, estrelas e data do último push
    rodape = ""
    x = 20
    if linguagem:
        cor = CORES_LINGUAGEM.get(linguagem, COR_APAGADO)
        rodape += (f'<circle cx="{x + 5}" cy="150" r="5" fill="{cor}"/>'
                   f'<text x="{x + 15}" y="154" class="meta">{esc(linguagem)}</text>')
        x += 15 + len(linguagem) * 6.5 + 14
    if repo["stargazers_count"]:
        rodape += f'<text x="{x:.0f}" y="154" class="meta">★ {repo["stargazers_count"]}</text>'
    rodape += f'<text x="{LARGURA - 20}" y="154" class="meta" text-anchor="end">{data}</text>'

    # Cada card entra com um pequeno atraso em relação ao anterior
    atraso = indice * 0.25

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{ALTURA}" viewBox="0 0 {LARGURA} {ALTURA}">
  <style>
    .card   {{ animation: surgir .8s ease-out {atraso}s both; }}
    .nome   {{ font: 600 16px {FONTE}; fill: {COR_DESTAQUE}; }}
    .desc   {{ font: 400 12.5px {FONTE}; fill: {COR_TEXTO}; }}
    .meta   {{ font: 400 11.5px {FONTE}; fill: {COR_APAGADO}; }}
    .topico {{ font: 500 10.5px {FONTE}; fill: {COR_DESTAQUE}; text-anchor: middle; }}
    .pilula {{ fill: {COR_DESTAQUE}; fill-opacity: .12; }}
    @keyframes surgir {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
  </style>
  <clipPath id="borda"><rect width="{LARGURA}" height="{ALTURA}" rx="12"/></clipPath>
  <g class="card">
    <g clip-path="url(#borda)">
      <rect width="{LARGURA}" height="{ALTURA}" fill="{COR_FUNDO}"/>
      <rect width="{LARGURA}" height="4" fill="{COR_DESTAQUE}"/>
    </g>
    <rect x=".5" y=".5" width="{LARGURA - 1}" height="{ALTURA - 1}" rx="12" fill="none" stroke="{COR_BORDA}"/>
    <text x="20" y="38" class="nome">{esc(nome)}</text>
    {descricao}
    {"".join(pilulas)}
    {rodape}
  </g>
</svg>
'''


# ================================================================ gravação
def salvar_cards(repos):
    """Grava os SVGs em cards/ e apaga cards antigos que sobrarem."""
    os.makedirs(PASTA_CARDS, exist_ok=True)
    gerados = []
    for i, repo in enumerate(repos, start=1):
        caminho = f"{PASTA_CARDS}/projeto-{i}.svg"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(gerar_svg(repo, i - 1))
        gerados.append(caminho)

    # Se antes havia mais cards do que agora, remove os que sobraram
    for antigo in glob.glob(f"{PASTA_CARDS}/projeto-*.svg"):
        if antigo not in gerados:
            os.remove(antigo)
    return gerados


def montar_bloco(repos, caminhos):
    """HTML que vai no README: os cards lado a lado, cada um clicável."""
    imagens = "\n".join(
        f'  <a href="{r["html_url"]}"><img src="./{c}" width="32%" alt="{esc(r["name"])}" /></a>'
        for r, c in zip(repos, caminhos)
    )
    return f'<p align="center">\n{imagens}\n</p>'


def atualizar_readme(bloco):
    """Troca o conteúdo entre os marcadores, sem tocar no resto do README."""
    with open(README, encoding="utf-8") as f:
        conteudo = f.read()

    padrao = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIM), re.DOTALL)
    if not padrao.search(conteudo):
        raise SystemExit(f"Marcadores {INICIO} / {FIM} não encontrados no {README}")

    # lambda evita que "\" no texto seja interpretado pelo re.sub
    novo = padrao.sub(lambda _: f"{INICIO}\n{bloco}\n{FIM}", conteudo)

    if novo != conteudo:
        with open(README, "w", encoding="utf-8") as f:
            f.write(novo)
        print("README atualizado.")
    else:
        print("README sem mudanças.")


if __name__ == "__main__":
    projetos = filtrar(buscar_repos())
    print("Projetos selecionados:", [p["name"] for p in projetos])
    if projetos:
        caminhos = salvar_cards(projetos)
        atualizar_readme(montar_bloco(projetos, caminhos))
    else:
        atualizar_readme("_Nenhum projeto com descrição ainda._")
