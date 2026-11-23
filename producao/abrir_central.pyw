"""Abre a central do Turismo Aqui no navegador padrão do Windows."""

import ctypes
import errno
import functools
import http.client
import http.server
import os
import re
import socket
import sys
import threading
import webbrowser
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORTAS = range(8000, 8011)
ERROS_DE_PORTA = {errno.EADDRINUSE, errno.EACCES, 10048, 10013}


class ServidorLocal(http.server.ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class ArquivosLocais(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        self.bytes_restantes = None
        faixa = re.fullmatch(r"bytes=(\d{0,20})-(\d{0,20})", self.headers.get("Range", ""))
        if not faixa or not any(faixa.groups()) or self.headers.get("If-Modified-Since"):
            return super().send_head()

        caminho = Path(self.translate_path(self.path))
        tipo = self.guess_type(caminho)
        if not tipo.startswith(("video/", "audio/")) or not caminho.is_file():
            return super().send_head()

        try:
            arquivo = caminho.open("rb")
        except OSError:
            return super().send_head()

        info = os.fstat(arquivo.fileno())
        modificado = self.date_time_string(info.st_mtime)
        if self.headers.get("If-Range", modificado) != modificado:
            arquivo.close()
            return super().send_head()

        tamanho = info.st_size
        primeiro, ultimo = faixa.groups()
        if primeiro:
            inicio = int(primeiro)
            fim = min(int(ultimo), tamanho - 1) if ultimo else tamanho - 1
        else:
            inicio = max(0, tamanho - int(ultimo))
            fim = tamanho - 1

        if inicio > fim:
            arquivo.close()
            self.send_response(http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{tamanho}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        arquivo.seek(inicio)
        self.bytes_restantes = fim - inicio + 1
        self.send_response(http.HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {inicio}-{fim}/{tamanho}")
        self.send_header("Content-Length", str(self.bytes_restantes))
        self.send_header("Last-Modified", modificado)
        self.end_headers()
        return arquivo

    def copyfile(self, origem, destino):
        if self.bytes_restantes is None:
            super().copyfile(origem, destino)
            return

        restantes = self.bytes_restantes
        while restantes:
            bloco = origem.read(min(restantes, 65536))
            if not bloco:
                break
            destino.write(bloco)
            restantes -= len(bloco)

    def log_message(self, formato, *args):
        if sys.stderr is not None:
            super().log_message(formato, *args)


def central_em_execucao(porta, pagina):
    conexao = http.client.HTTPConnection(HOST, porta, timeout=0.75)
    try:
        conexao.request("GET", "/index.html")
        resposta = conexao.getresponse()
        return resposta.status == 200 and resposta.read(len(pagina) + 1) == pagina
    except (OSError, http.client.HTTPException):
        return False
    finally:
        conexao.close()


def abrir_navegador(url):
    if not webbrowser.open(url, new=2):
        os.startfile(url)


def iniciar_central():
    pagina = (RAIZ / "index.html").read_bytes()
    handler = functools.partial(ArquivosLocais, directory=RAIZ)
    for porta in PORTAS:
        url = f"http://{HOST}:{porta}/"
        try:
            servidor = ServidorLocal((HOST, porta), handler)
        except OSError as erro:
            if erro.errno not in ERROS_DE_PORTA and getattr(erro, "winerror", None) not in ERROS_DE_PORTA:
                raise
            if central_em_execucao(porta, pagina):
                abrir_navegador(url)
                return
            continue

        with servidor:
            thread = threading.Thread(target=servidor.serve_forever, daemon=True)
            thread.start()
            try:
                abrir_navegador(url)
                thread.join()
            finally:
                servidor.shutdown()
        return
    raise OSError("As portas locais de 8000 a 8010 estão ocupadas.")


if __name__ == "__main__":
    try:
        iniciar_central()
    except OSError as erro:
        ctypes.windll.user32.MessageBoxW(
            None, f"Não foi possível abrir a Central Turismo Aqui.\n\n{erro}", "Turismo Aqui", 0x10
        )
