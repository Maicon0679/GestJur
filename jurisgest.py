#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MF System Jur — Lançador Windows
Versão: 2.0
Requer: Python 3.8+  |  pip install pywebview requests beautifulsoup4
"""

import sys
import os
import json
import threading
import socket
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

APP_NAME   = "MF System Jur"
HTML_FILE  = "sistema_juridico_pro.html"
START_PORT = 18734


# ──────────────────────────────────────────────
#  Utilitários
# ──────────────────────────────────────────────

def resource_path(filename):
    """Resolve caminho de arquivo — funciona tanto no .py quanto no .exe (PyInstaller)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def find_free_port(start=START_PORT):
    """Encontra uma porta TCP livre a partir de `start`."""
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


def show_error(title, message):
    """Exibe MessageBox nativa do Windows."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        print(f"ERRO — {title}\n{message}", file=sys.stderr)


def hide_console():
    """Oculta a janela do console no Windows."""
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


# ──────────────────────────────────────────────
#  APIs de publicações
# ──────────────────────────────────────────────

def buscar_datajud(oab: str, nome: str, apikey: str,
                   dt_ini: str = "", dt_fim: str = "") -> dict:
    """
    Consulta a API pública do DataJud (CNJ).
    Documentação: https://datajud-wiki.cnj.jus.br/api-publica/
    Cadastro gratuito em: https://datajud.cnj.jus.br/
    """
    try:
        import requests
    except ImportError:
        return {"erro": "Módulo 'requests' não instalado. Execute: pip install requests", "resultados": []}

    resultados = []

    # Tribunais cobrindo o Rio de Janeiro
    tribunais = [
        ("TJRJ", "api_publica_tjrj"),
        ("TRT1", "api_publica_trt1"),
        ("TRF2", "api_publica_trf2"),
    ]

    headers = {
        "Authorization": f"ApiKey {apikey}" if apikey else "ApiKey cnjMjM4NjE4NTI5MDM4OTU6aDZsVGZCZk8=",
        "Content-Type": "application/json",
    }

    for tribunal_nome, tribunal_indice in tribunais:
        try:
            # Montar query Elasticsearch
            must_clauses = []
            if oab:
                must_clauses.append({
                    "match": {"movimentos.complementosTabelados.descricao": f"OAB {oab}"}
                })
            if nome:
                must_clauses.append({
                    "match": {"partes.nome": nome}
                })

            body = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}]
                    }
                },
                "sort": [{"dataAjuizamento": {"order": "desc"}}],
                "size": 20,
                "_source": ["numeroProcesso", "dataAjuizamento", "classeProcessual",
                            "assuntos", "movimentos", "partes", "tribunal", "orgaoJulgador"]
            }

            # Filtro de data
            if dt_ini or dt_fim:
                range_filter = {"range": {"dataAjuizamento": {}}}
                if dt_ini:
                    range_filter["range"]["dataAjuizamento"]["gte"] = dt_ini
                if dt_fim:
                    range_filter["range"]["dataAjuizamento"]["lte"] = dt_fim
                body["query"]["bool"]["filter"] = [range_filter]

            url = f"https://api-publica.datajud.cnj.jus.br/{tribunal_indice}/_search"
            resp = requests.post(url, headers=headers, json=body, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", {}).get("hits", [])
                for hit in hits:
                    src = hit.get("_source", {})
                    numero = src.get("numeroProcesso", "")
                    movs = src.get("movimentos", [])
                    ultimo_mov = movs[0] if movs else {}
                    partes = src.get("partes", [])
                    nomes_partes = " × ".join(
                        p.get("nome", "") for p in partes[:2] if p.get("nome")
                    )
                    assuntos = src.get("assuntos", [])
                    assunto = assuntos[0].get("descricao", "") if assuntos else ""
                    orgao = (src.get("orgaoJulgador") or {}).get("nome", "")

                    resultados.append({
                        "refId": f"datajud_{hit.get('_id', numero)}",
                        "numero": numero,
                        "titulo": f"{tribunal_nome} — {src.get('classeProcessual', {}).get('descricao', '')}",
                        "tipo": ultimo_mov.get("nome", "Andamento"),
                        "data": (ultimo_mov.get("dataHora", "") or "")[:10],
                        "texto": f"Partes: {nomes_partes}\nAssunto: {assunto}\nÓrgão: {orgao}\n\nÚltimo movimento: {ultimo_mov.get('nome', '')} em {(ultimo_mov.get('dataHora','')or '')[:10]}",
                        "tribunal": tribunal_nome,
                        "orgao": orgao,
                        "url": f"https://datajud.cnj.jus.br/TJRJ/_search?query={numero}",
                    })
        except Exception as e:
            print(f"[DataJud/{tribunal_nome}] Erro: {e}", file=sys.stderr)
            continue

    return {"resultados": resultados, "total": len(resultados)}


def buscar_djerj(oab: str, nome: str,
                 dt_ini: str = "", dt_fim: str = "") -> dict:
    """
    Busca publicações no Diário da Justiça Eletrônico do TJRJ.
    URL base: https://dje.tjrj.jus.br/
    """
    try:
        import requests
        from html.parser import HTMLParser
    except ImportError:
        return {"erro": "Módulo 'requests' não instalado. Execute: pip install requests", "resultados": []}

    resultados = []

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })

        # Parâmetros de busca do DJe RJ
        params = {
            "tipoConsulta": "advogado",
            "nomeParte": nome or "",
            "nroOAB": oab or "",
            "dtIni": dt_ini.replace("-", "/") if dt_ini else "",
            "dtFim": dt_fim.replace("-", "/") if dt_fim else "",
            "submit": "Pesquisar",
        }

        resp = session.post(
            "https://dje.tjrj.jus.br/ConsultaPublicacao/pesquisar.do",
            data=params,
            timeout=20
        )

        if resp.status_code != 200:
            return {"erro": f"DJe RJ retornou status {resp.status_code}", "resultados": []}

        # Extração simples com regex (evita dependência do BeautifulSoup)
        html = resp.text

        # Procurar blocos de publicação (padrão do DJe RJ)
        blocos = re.findall(
            r'<tr[^>]*class="[^"]*resultadoPesquisa[^"]*"[^>]*>(.*?)</tr>',
            html, re.DOTALL | re.IGNORECASE
        )

        if not blocos:
            # Tentar padrão alternativo
            blocos = re.findall(r'<div[^>]*class="[^"]*publicacao[^"]*"[^>]*>(.*?)</div>',
                                html, re.DOTALL | re.IGNORECASE)

        for i, bloco in enumerate(blocos[:20]):
            # Limpar HTML
            texto = re.sub(r'<[^>]+>', ' ', bloco)
            texto = re.sub(r'\s+', ' ', texto).strip()
            if len(texto) < 20:
                continue

            # Tentar extrair número do processo
            num_match = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto)
            numero = num_match.group(0) if num_match else ""

            # Tentar extrair data
            data_match = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
            data_str = ""
            if data_match:
                d = data_match.group(1)
                data_str = f"{d[6:]}-{d[3:5]}-{d[:2]}"

            resultados.append({
                "refId": f"djerj_{i}_{oab}_{data_str}",
                "numero": numero,
                "titulo": f"DJe RJ — Publicação{'  · ' + numero if numero else ''}",
                "tipo": "Publicação DJe",
                "data": data_str,
                "texto": texto[:1000],
                "tribunal": "TJRJ",
                "orgao": "",
                "url": "https://dje.tjrj.jus.br/",
            })

    except Exception as e:
        print(f"[DJe RJ] Erro: {e}", file=sys.stderr)
        return {"erro": str(e), "resultados": resultados}

    return {"resultados": resultados, "total": len(resultados)}



# ──────────────────────────────────────────────
#  Consulta CPF / CNPJ (via APIs públicas)
# ──────────────────────────────────────────────

def consultar_cpf(num: str) -> dict:
    """Consulta CPF na API da Receita Federal (via receitaws.com.br — gratuito)."""
    try:
        import requests
    except ImportError:
        return {"erro": "requests não instalado"}
    try:
        num = "".join(filter(str.isdigit, num))
        r = requests.get(
            f"https://www.receitaws.com.br/v1/cpf/{num}",
            timeout=10,
            headers={"User-Agent": "MFSystemJur/2.0"}
        )
        if r.status_code == 200:
            d = r.json()
            return {"nome": d.get("nome", ""), "situacao": d.get("situacao", ""),
                    "nascimento": d.get("nascimento", ""), "municipio": d.get("municipio", "")}
        return {"erro": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"erro": str(e)}


def consultar_cnpj(num: str) -> dict:
    """Consulta CNPJ na API da Receita Federal (via receitaws.com.br — gratuito)."""
    try:
        import requests
    except ImportError:
        return {"erro": "requests não instalado"}
    try:
        num = "".join(filter(str.isdigit, num))
        r = requests.get(
            f"https://www.receitaws.com.br/v1/cnpj/{num}",
            timeout=10,
            headers={"User-Agent": "MFSystemJur/2.0"}
        )
        if r.status_code == 200:
            d = r.json()
            ativs = d.get("atividade_principal", [])
            ativ = ativs[0].get("text", "") if ativs else ""
            return {
                "nome": d.get("nome", ""),
                "fantasia": d.get("fantasia", ""),
                "situacao": d.get("situacao", ""),
                "municipio": d.get("municipio", ""),
                "uf": d.get("uf", ""),
                "abertura": d.get("abertura", ""),
                "atividade": ativ,
            }
        return {"erro": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"erro": str(e)}


# ──────────────────────────────────────────────
#  Backup automático agendado
# ──────────────────────────────────────────────

def iniciar_backup_agendado(app_dir: str, intervalo_horas: int = 24):
    """Salva backup automático do localStorage a cada N horas (requer dados exportados pelo frontend)."""
    import threading, os, datetime
    backup_dir = os.path.join(app_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    def _loop():
        while True:
            time.sleep(intervalo_horas * 3600)
            # O backup real é feito quando o frontend chama /api/backup com o JSON
            print(f"[Backup] Próximo backup agendado em {intervalo_horas}h", flush=True)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


# ──────────────────────────────────────────────
#  Servidor HTTP com roteamento de API
# ──────────────────────────────────────────────

class MFSystemHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, app_dir=None, **kwargs):
        self._app_dir = app_dir
        super().__init__(*args, **kwargs)

    def log_message(self, fmt, *args):
        pass   # silencioso

    def log_error(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path == "/api/backup":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                import datetime, os
                backup_dir = os.path.join(self._app_dir, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = os.path.join(backup_dir, f"backup_{ts}.json")
                with open(fname, "wb") as bf:
                    bf.write(body)
                self.send_json({"ok": True, "arquivo": fname})
            except Exception as e:
                self.send_json({"ok": False, "erro": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        qs     = parse_qs(parsed.query)

        def qs1(key):
            return unquote(qs.get(key, [""])[0])

        # ── Ping ──
        if path == "/api/ping":
            self.send_json({"ok": True, "app": APP_NAME})
            return

        # ── CPF / CNPJ ──
        if path == "/api/cpf":
            num = qs1("num")
            tipo = qs1("tipo")
            if tipo == "cnpj":
                self.send_json(consultar_cnpj(num))
            else:
                self.send_json(consultar_cpf(num))
            return

        # ── Backup receber ──
        if path == "/api/backup":
            self.send_json({"ok": True, "msg": "Use POST /api/backup para salvar dados."})
            return

        # ── DataJud CNJ ──
        if path == "/api/datajud":
            result = buscar_datajud(
                oab=qs1("oab"),
                nome=qs1("nome"),
                apikey=qs1("apikey"),
                dt_ini=qs1("dtIni"),
                dt_fim=qs1("dtFim"),
            )
            self.send_json(result)
            return

        # ── DJe RJ ──
        if path == "/api/djerj":
            result = buscar_djerj(
                oab=qs1("oab"),
                nome=qs1("nome"),
                dt_ini=qs1("dtIni"),
                dt_fim=qs1("dtFim"),
            )
            self.send_json(result)
            return

        # ── Arquivos estáticos ──
        if path == "" or path == "/":
            path = f"/{HTML_FILE}"

        file_path = os.path.join(self._app_dir, path.lstrip("/"))
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            mime = {
                ".html": "text/html; charset=utf-8",
                ".js":   "application/javascript",
                ".css":  "text/css",
                ".png":  "image/png",
                ".ico":  "image/x-icon",
            }.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def start_server(directory: str, port: int) -> HTTPServer:
    """Inicia o servidor HTTP com suporte a APIs."""
    def handler_factory(*args, **kwargs):
        return MFSystemHandler(*args, app_dir=directory, **kwargs)

    server = HTTPServer(("127.0.0.1", port), handler_factory)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ──────────────────────────────────────────────
#  Ponto de entrada
# ──────────────────────────────────────────────

def main():
    hide_console()

    # 1. Verificar arquivo HTML
    html_path = resource_path(HTML_FILE)
    if not os.path.exists(html_path):
        show_error(
            f"{APP_NAME} — Arquivo não encontrado",
            f"O arquivo '{HTML_FILE}' não foi localizado.\n\n"
            "Certifique-se de que ele está na mesma pasta do programa."
        )
        sys.exit(1)

    app_dir = os.path.dirname(html_path)

    # 2. Instalar requests/beautifulsoup4 silenciosamente se necessário
    try:
        import requests  # noqa
    except ImportError:
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "--quiet"],
            capture_output=True
        )

    # 3. Iniciar servidor HTTP
    port = find_free_port()
    start_server(app_dir, port)
    time.sleep(0.3)

    url = f"http://127.0.0.1:{port}/{HTML_FILE}"

    # 4. Abrir janela nativa com pywebview
    try:
        import webview

        window = webview.create_window(
            title    = f"{APP_NAME} — Sistema de Gestão Jurídica",
            url      = url,
            width    = 1440,
            height   = 900,
            min_size = (1024, 640),
            text_select   = True,
            zoomable      = True,
            confirm_close = True,
        )

        try:
            webview.start(gui="edgechromium", private_mode=False, debug=False)
        except Exception:
            webview.start(private_mode=False)

    except ImportError:
        import webbrowser
        webbrowser.open(url)
        show_error(
            f"{APP_NAME} — Aviso",
            "O módulo 'pywebview' não está instalado.\n"
            "O sistema foi aberto no navegador padrão.\n\n"
            "Para instalar: pip install pywebview"
        )
    except Exception as ex:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            show_error(f"{APP_NAME} — Erro", str(ex))


if __name__ == "__main__":
    main()
