/**
 * Lógica da página /painel/categorias (listar, criar e excluir categorias).
 */

const token = sessionStorage.getItem("Stokfy_token");

if (!token) {
    window.location.href = "/login";
}

document.getElementById("logout-btn").addEventListener("click", () => {
    sessionStorage.removeItem("Stokfy_token");
    window.location.href = "/login";
});

function criarLinhaCategoria(categoria) {
    const linha = document.createElement("tr");

    linha.innerHTML = `
        <td class="stock-table__nome">${categoria.nome}</td>
        <td class="stock-table__acoes">
            <button class="btn-acao btn-acao--perigo" data-acao="excluir" data-id="${categoria.id}">Excluir</button>
        </td>
    `;

    return linha;
}

async function carregarCategorias() {
    const carregando = document.getElementById("categorias-estado-carregando");
    const vazio = document.getElementById("categorias-estado-vazio");
    const erro = document.getElementById("categorias-estado-erro");
    const tabela = document.getElementById("categorias-tabela");
    const tbody = document.getElementById("categorias-tbody");
    const contagem = document.getElementById("categorias-contagem");

    carregando.hidden = false;
    vazio.hidden = true;
    erro.hidden = true;
    tabela.hidden = true;
    tbody.innerHTML = "";

    try {
        const resposta = await fetch("/categorias", {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (resposta.status === 401) {
            sessionStorage.removeItem("Stokfy_token");
            window.location.href = "/login";
            return;
        }

        if (!resposta.ok) {
            throw new Error("Falha ao buscar categorias");
        }

        const categorias = await resposta.json();

        carregando.hidden = true;

        if (categorias.length === 0) {
            vazio.hidden = false;
            contagem.textContent = "Nenhuma categoria cadastrada";
            return;
        }

        categorias.forEach((categoria) => {
            tbody.appendChild(criarLinhaCategoria(categoria));
        });

        tabela.hidden = false;
        contagem.textContent =
            categorias.length === 1 ? "1 categoria cadastrada" : `${categorias.length} categorias cadastradas`;
    } catch (falha) {
        carregando.hidden = true;
        erro.hidden = false;
    }
}

const form = document.getElementById("categoria-form");
const formErro = document.getElementById("categoria-form-error");
const botaoSalvar = document.getElementById("salvar-categoria-btn");
const inputNome = document.getElementById("categoria-nome");

form.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    formErro.hidden = true;
    botaoSalvar.disabled = true;
    botaoSalvar.textContent = "Adicionando...";

    try {
        const resposta = await fetch("/categorias", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ nome: inputNome.value }),
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível criar a categoria.");
        }

        inputNome.value = "";
        carregarCategorias();
    } catch (falha) {
        formErro.textContent = falha.message;
        formErro.hidden = false;
    } finally {
        botaoSalvar.disabled = false;
        botaoSalvar.textContent = "Adicionar";
    }
});

document.getElementById("categorias-tbody").addEventListener("click", async (evento) => {
    const botao = evento.target.closest("button[data-acao='excluir']");
    if (!botao) return;

    const id = parseInt(botao.dataset.id);
    const linha = botao.closest("tr");
    const nome = linha.querySelector(".stock-table__nome").textContent;

    const confirmou = window.confirm(`Tem certeza que deseja excluir a categoria "${nome}"?`);
    if (!confirmou) return;

    try {
        const resposta = await fetch(`/categorias/${id}`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível excluir a categoria.");
        }

        carregarCategorias();
    } catch (falha) {
        alert(falha.message);
    }
});

carregarCategorias();