"use strict";

const publicacoes = window.catalogoVisual;
const busca = document.querySelector("#busca");
const situacao = document.querySelector("#situacao");
const lista = document.querySelector("#videos");
const resultado = document.querySelector("#resultado");
const mais = document.querySelector("#mais");
const formato = new Intl.NumberFormat("pt-BR");
const porPagina = 24;
let limite = porPagina;

function normalizar(texto) {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

function inserir(pai, tipo, texto, classe) {
  const elemento = document.createElement(tipo);
  if (texto) elemento.textContent = texto;
  if (classe) elemento.className = classe;
  pai.append(elemento);
  return elemento;
}

function cartao(video) {
  const item = document.createElement("li");
  if (video.capa) {
    const imagem = inserir(item, "img", "", "capa");
    imagem.src = video.capa;
    imagem.alt = "";
    imagem.loading = "lazy";
  }
  const texto = inserir(item, "div", "", "video-texto");
  const data = video.data.split("-").reverse().join("/");
  inserir(texto, "p", `${video.tipo} · ${data} · ${video.duracao}`, "origem");
  const titulo = inserir(texto, "h2");
  const link = inserir(titulo, "a", video.titulo);
  link.href = video.ficha || video.url;
  const contagem = `${video.quantidade} ${video.quantidade === 1 ? "quadro" : "quadros"}`;
  inserir(texto, "p", video.estado === "Completo" ? contagem : `${video.estado} · ${contagem}`, "local");
  if (video.motivo) inserir(texto, "p", video.motivo, "origem");
  return item;
}

function exibir() {
  const termos = normalizar(busca.value).trim().split(/\s+/);
  const filtro = situacao.value;
  const encontrados = publicacoes.filter((video) => {
    const corresponde = filtro === "todas" || filtro === video.estado || (filtro === "com-quadros" && video.quantidade > 0);
    const texto = normalizar([video.titulo, video.id, ...(video.locais || [])].join(" "));
    return corresponde && termos.every((termo) => texto.includes(termo));
  });
  lista.replaceChildren(...encontrados.slice(0, limite).map(cartao));
  resultado.textContent = encontrados.length
    ? `Exibindo ${Math.min(limite, encontrados.length)} de ${formato.format(encontrados.length)} publicações`
    : "Nenhuma publicação encontrada.";
  mais.hidden = encontrados.length <= limite;
}

function reiniciar() {
  limite = porPagina;
  exibir();
}

const total = publicacoes.reduce((soma, video) => soma + video.quantidade, 0);
const completos = publicacoes.filter((video) => video.estado === "Completo").length;
const pendentes = publicacoes.filter((video) => video.estado === "Pendente").length;
document.querySelector("#resumo").textContent = `${formato.format(total)} quadros revisados · ${formato.format(completos)} de ${formato.format(publicacoes.length)} publicações com 10 ou mais quadros · ${formato.format(pendentes)} pendentes`;

document.querySelector("#filtros").addEventListener("submit", (evento) => evento.preventDefault());
busca.addEventListener("input", reiniciar);
situacao.addEventListener("change", reiniciar);
mais.addEventListener("click", () => {
  limite += porPagina;
  exibir();
});
exibir();
