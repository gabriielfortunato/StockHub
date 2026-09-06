/**
 * Lógica da página /painel (listar, criar, editar, excluir produtos
 * e registrar entradas/saídas de estoque).
 */

const token = sessionStorage.getItem("Stokfy_token");

if (!token) {
    window.location.href = "/login";
}

document.getElementById("logout-btn").addEventListener("click", () => {
    sessionStorage.removeItem("Stokfy_token");
    window.location.href = "/login";
});

function formatarPreco(valor) {
    return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

let produtosCache = [];

function criarLinhaProduto(produto) {
    const linha = document.createElement("tr");

    const estoqueBaixo = produto.quantidade_atual <= produto.estoque_minimo;

    linha.innerHTML = `
        <td class="stock-table__sku">${produto.sku || "—"}</td>
        <td class="stock-table__nome">${produto.nome}</td>
        <td class="stock-table__preco">${formatarPreco(produto.preco_venda)}</td>
        <td class="stock-table__qtd">${produto.quantidade_atual} un${estoqueBaixo ? ' <span class="badge-baixo">Repor estoque</span>' : ""}</td>
        <td class="stock-table__acoes">
            <button class="btn-acao btn-acao--destaque" data-acao="movimentar" data-id="${produto.id}">Movimentar</button>
            <button class="btn-acao" data-acao="editar" data-id="${produto.id}">Editar</button>
            <button class="btn-acao btn-acao--perigo" data-acao="excluir" data-id="${produto.id}">Excluir</button>
        </td>
    `;

    return linha;
}

async function carregarProdutos() {
    const carregando = document.getElementById("produtos-estado-carregando");
    const vazio = document.getElementById("produtos-estado-vazio");
    const erro = document.getElementById("produtos-estado-erro");
    const tabela = document.getElementById("produtos-tabela");
    const tbody = document.getElementById("produtos-tbody");
    const contagem = document.getElementById("produtos-contagem");

    carregando.hidden = false;
    vazio.hidden = true;
    erro.hidden = true;
    tabela.hidden = true;
    tbody.innerHTML = "";

    try {
        const resposta = await fetch("/produtos", {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (resposta.status === 401) {
            sessionStorage.removeItem("Stokfy_token");
            window.location.href = "/login";
            return;
        }

        if (!resposta.ok) {
            throw new Error("Falha ao buscar produtos");
        }

        const produtos = await resposta.json();
        produtosCache = produtos;

        carregando.hidden = true;

        if (produtos.length === 0) {
            vazio.hidden = false;
            contagem.textContent = "Nenhum produto cadastrado";
            return;
        }

        produtos.forEach((produto) => {
            tbody.appendChild(criarLinhaProduto(produto));
        });

        tabela.hidden = false;
        contagem.textContent =
            produtos.length === 1 ? "1 produto cadastrado" : `${produtos.length} produtos cadastrados`;
    } catch (falha) {
        carregando.hidden = true;
        erro.hidden = false;
    }
}

/**
 * Modal "Novo produto" / "Editar produto".
 */
const overlay = document.getElementById("modal-overlay");
const form = document.getElementById("produto-form");
const formErro = document.getElementById("produto-form-error");
const selectCategoria = document.getElementById("produto-categoria");
const modalTitulo = document.getElementById("modal-titulo");
const botaoSalvar = document.getElementById("salvar-produto-btn");

let produtoEmEdicaoId = null;

async function carregarCategoriasNoSelect(categoriaSelecionadaId) {
    try {
        const resposta = await fetch("/categorias", {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!resposta.ok) return;

        const categorias = await resposta.json();

        selectCategoria.innerHTML = '<option value="">Sem categoria</option>';

        categorias.forEach((categoria) => {
            const opcao = document.createElement("option");
            opcao.value = categoria.id;
            opcao.textContent = categoria.nome;
            if (categoriaSelecionadaId && categoria.id === categoriaSelecionadaId) {
                opcao.selected = true;
            }
            selectCategoria.appendChild(opcao);
        });
    } catch (falha) {
        // Se falhar, o select simplesmente fica só com "Sem categoria".
    }
}

function abrirModalNovoProduto() {
    produtoEmEdicaoId = null;
    formErro.hidden = true;
    form.reset();
    modalTitulo.textContent = "Novo produto";
    botaoSalvar.textContent = "Salvar produto";
    carregarCategoriasNoSelect(null);
    overlay.classList.add("is-open");
}

function abrirModalEditarProduto(produto) {
    produtoEmEdicaoId = produto.id;
    formErro.hidden = true;
    modalTitulo.textContent = "Editar produto";
    botaoSalvar.textContent = "Salvar alterações";

    document.getElementById("produto-nome").value = produto.nome;
    document.getElementById("produto-sku").value = produto.sku || "";
    document.getElementById("produto-preco-custo").value = produto.preco_custo;
    document.getElementById("produto-preco-venda").value = produto.preco_venda;
    document.getElementById("produto-estoque-minimo").value = produto.estoque_minimo;

    carregarCategoriasNoSelect(produto.categoria_id);
    overlay.classList.add("is-open");
}

function fecharModal() {
    overlay.classList.remove("is-open");
}

document.getElementById("abrir-modal-btn").addEventListener("click", abrirModalNovoProduto);
document.getElementById("fechar-modal-btn").addEventListener("click", fecharModal);
document.getElementById("cancelar-modal-btn").addEventListener("click", fecharModal);

overlay.addEventListener("click", (evento) => {
    if (evento.target === overlay) fecharModal();
});

form.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    formErro.hidden = true;

    const dados = {
        nome: document.getElementById("produto-nome").value,
        sku: document.getElementById("produto-sku").value || null,
        preco_custo: parseFloat(document.getElementById("produto-preco-custo").value) || 0,
        preco_venda: parseFloat(document.getElementById("produto-preco-venda").value) || 0,
        estoque_minimo: parseInt(document.getElementById("produto-estoque-minimo").value) || 0,
        categoria_id: selectCategoria.value ? parseInt(selectCategoria.value) : null,
    };

    const estaEditando = produtoEmEdicaoId !== null;
    const url = estaEditando ? `/produtos/${produtoEmEdicaoId}` : "/produtos";
    const metodo = estaEditando ? "PUT" : "POST";

    botaoSalvar.disabled = true;
    botaoSalvar.textContent = "Salvando...";

    try {
        const resposta = await fetch(url, {
            method: metodo,
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(dados),
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível salvar o produto. Confira os dados.");
        }

        fecharModal();
        carregarProdutos();
    } catch (falha) {
        formErro.textContent = falha.message;
        formErro.hidden = false;
    } finally {
        botaoSalvar.disabled = false;
        botaoSalvar.textContent = estaEditando ? "Salvar alterações" : "Salvar produto";
    }
});

/**
 * Modal "Movimentar estoque" (entrada/saída).
 */
const movOverlay = document.getElementById("mov-overlay");
const movForm = document.getElementById("mov-form");
const movFormErro = document.getElementById("mov-form-error");
const movProdutoNome = document.getElementById("mov-produto-nome");
const movSalvarBtn = document.getElementById("mov-salvar-btn");

let produtoEmMovimentacaoId = null;

function abrirModalMovimentacao(produto) {
    produtoEmMovimentacaoId = produto.id;
    movFormErro.hidden = true;
    movForm.reset();
    movProdutoNome.textContent = `${produto.nome} — estoque atual: ${produto.quantidade_atual} un`;
    movOverlay.classList.add("is-open");
}

function fecharModalMovimentacao() {
    movOverlay.classList.remove("is-open");
}

document.getElementById("mov-fechar-btn").addEventListener("click", fecharModalMovimentacao);
document.getElementById("mov-cancelar-btn").addEventListener("click", fecharModalMovimentacao);

movOverlay.addEventListener("click", (evento) => {
    if (evento.target === movOverlay) fecharModalMovimentacao();
});

movForm.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    movFormErro.hidden = true;

    const dados = {
        produto_id: produtoEmMovimentacaoId,
        tipo: document.getElementById("mov-tipo").value,
        quantidade: parseInt(document.getElementById("mov-quantidade").value),
        motivo: document.getElementById("mov-motivo").value || null,
    };

    movSalvarBtn.disabled = true;
    movSalvarBtn.textContent = "Salvando...";

    try {
        const resposta = await fetch("/movimentacoes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(dados),
        });

        if (!resposta.ok) {
            const detalhe = await resposta.json().catch(() => null);
            throw new Error(detalhe?.detail || "Não foi possível registrar a movimentação.");
        }

        fecharModalMovimentacao();
        carregarProdutos();
    } catch (falha) {
        movFormErro.textContent = falha.message;
        movFormErro.hidden = false;
    } finally {
        movSalvarBtn.disabled = false;
        movSalvarBtn.textContent = "Confirmar";
    }
});

/**
 * Ações da tabela: editar, excluir, movimentar.
 */
document.getElementById("produtos-tbody").addEventListener("click", async (evento) => {
    const botao = evento.target.closest("button[data-acao]");
    if (!botao) return;

    const id = parseInt(botao.dataset.id);
    const acao = botao.dataset.acao;
    const produto = produtosCache.find((p) => p.id === id);

    if (acao === "movimentar") {
        if (produto) abrirModalMovimentacao(produto);
        return;
    }

    if (acao === "editar") {
        if (produto) abrirModalEditarProduto(produto);
        return;
    }

    if (acao === "excluir") {
        const nome = produto ? produto.nome : "este produto";
        const confirmou = window.confirm(`Tem certeza que deseja excluir "${nome}"? Essa ação não pode ser desfeita.`);
        if (!confirmou) return;

        try {
            const resposta = await fetch(`/produtos/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!resposta.ok) {
                throw new Error("Não foi possível excluir o produto.");
            }

            carregarProdutos();
        } catch (falha) {
            alert(falha.message);
        }
    }
});

carregarProdutos();