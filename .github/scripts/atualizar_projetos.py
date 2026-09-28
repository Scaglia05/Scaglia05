"""
Atualiza a seção de projetos do README com os repositórios mais recentes.

Fluxo:
  1. Busca na API do GitHub os repositórios do usuário, ordenados pelo último push.
  2. Filtra: ignora forks, arquivados, o próprio repo do perfil, repos sem
     descrição ("About") e repos marcados com o tópico "ocultar-perfil".
  3. Gera um bloco <details> para cada projeto usando o About como descrição.
  4. Substitui o que estiver entre os marcadores PROJETOS:INICIO e PROJETOS:FIM.

Sem dependências externas: só a biblioteca padrão do Python.
"""

import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

# ---------------------------------------------------------------- configuração
USUARIO = os.environ.get("GITHUB_USER", "Scaglia05")
TOKEN = os.environ.get("GITHUB_TOKEN")      # opcional localmente, a Action fornece
QUANTIDADE = 5                              # quantos projetos mostrar
TOPICO_OCULTAR = "ocultar-perfil"           # adicione esse tópico a um repo para escondê-lo
README = "README.md"
INICIO = "<!-- PROJETOS:INICIO -->"
FIM = "<!-- PROJETOS:FIM -->"

# Linguagem principal do repo -> (logo do shields.io, cor de fundo do badge)
LINGUAGENS = {
    "C#":         ("dotnet",     "512BD4"),
    "Python":     ("python",     "3776AB"),
    "JavaScript": ("javascript", "F7DF1E"),
    "TypeScript": ("typescript", "3178C6"),
    "HTML":       ("html5",      "E34F26"),
    "CSS":        ("css3",       "1572B6"),
    "C++":        ("cplusplus",  "00599C"),
    "C":          ("c",          "A8B9CC"),
    "Jupyter Notebook": ("jupyter", "F37626"),
}


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


def badge_linguagem(linguagem):
    """Monta o badge da linguagem principal (ou nada, se o repo não tiver uma)."""
    if not linguagem:
        return ""
    logo, cor = LINGUAGENS.get(linguagem, ("", "555555"))
    # No shields.io, "-" vira "--" e espaço vira "_" dentro do texto do badge
    texto = urllib.parse.quote(linguagem.replace("-", "--").replace(" ", "_"))
    url = f"https://img.shields.io/badge/{texto}-{cor}?style=flat-square"
    if logo:
        url += f"&logo={logo}&logoColor=white"
    return f'<img src="{url}" alt="{html.escape(linguagem)}" />'


def renderizar(repo, aberto):
    """Gera o bloco <details> de um projeto."""
    nome = html.escape(repo["name"])
    descricao = html.escape(repo["description"])
    linguagem = repo.get("language") or ""
    data = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")

    # Tópicos do repo viram "tags" abaixo da descrição
    topicos = " ".join(f"<code>{html.escape(t)}</code>"
                       for t in repo.get("topics", []) if t != TOPICO_OCULTAR)

    # Linha de links: repositório, demo (campo Website do About) e estrelas
    links = [f"🔗 [Ver repositório]({repo['html_url']})"]
    if repo.get("homepage"):
        links.append(f"🌐 [Demo]({repo['homepage']})")
    if repo["stargazers_count"]:
        links.append(f"⭐ {repo['stargazers_count']}")
    links.append(f"🕒 Atualizado em {data}")

    resumo = f"<b>📁 {nome}</b>" + (f" · {html.escape(linguagem)}" if linguagem else "")
    partes = [
        f"<details{' open' if aberto else ''}>",
        f"<summary>{resumo}</summary>",
        "<br/>",
        "",
        badge_linguagem(linguagem),
        "",
        descricao,
        "",
    ]
    if topicos:
        partes += [topicos, ""]
    partes += [" · ".join(links), "</details>", ""]
    return "\n".join(partes)


def atualizar_readme(bloco):
    """Troca o conteúdo entre os marcadores, sem tocar no resto do README."""
    with open(README, encoding="utf-8") as f:
        conteudo = f.read()

    padrao = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIM), re.DOTALL)
    if not padrao.search(conteudo):
        raise SystemExit(f"Marcadores {INICIO} / {FIM} não encontrados no {README}")

    # lambda evita que "\" na descrição seja interpretado pelo re.sub
    novo = padrao.sub(lambda _: f"{INICIO}\n{bloco}\n{FIM}", conteudo)

    if novo != conteudo:
        with open(README, "w", encoding="utf-8") as f:
            f.write(novo)
        print("README atualizado.")
    else:
        print("Nada mudou.")


if __name__ == "__main__":
    projetos = filtrar(buscar_repos())
    print("Projetos selecionados:", [p["name"] for p in projetos])
    if projetos:
        blocos = [renderizar(p, aberto=(i == 0)) for i, p in enumerate(projetos)]
        atualizar_readme("\n".join(blocos))
    else:
        atualizar_readme("_Nenhum projeto com descrição ainda._\n")
