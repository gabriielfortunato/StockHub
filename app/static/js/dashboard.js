/**
 * Painel Stokfy: produtos, movimentações e leitura de códigos de barras.
 */
const token = sessionStorage.getItem("stockhub_token");
if (!token) window.location.href = "/login";

document.getElementById("logout-btn").addEventListener("click", () => {
    sessionStorage.removeItem("stockhub_token");
    window.location.href = "/login";
});

function tratarBloqueioOuDeslogado(resposta) {
    if (resposta.status === 401) {
        sessionStorage.removeItem("stockhub_token");
        window.location.href = "/login";
        return true;
    }
    if (resposta.status === 402) {
        window.location.href = "/renovar";
        return true;
    }
    return false;
}

let planoVencido = false;
async function verificarPlano() {
    const resposta = await fetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    if (resposta.status === 401) {
        sessionStorage.removeItem("stockhub_token");
        window.location.href = "/login";
        return;
    }
    if (!resposta.ok) return;
    const loja = await resposta.json();
    planoVencido = Boolean(loja.plano_vencido);
    if (planoVencido) {
        document.getElementById("plano-vencido-aviso").hidden = false;
        document.getElementById("abrir-modal-btn").disabled = true;
    }
}

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
            ${planoVencido ? "Somente leitura" : `<button class="btn-acao btn-acao--destaque" data-acao="movimentar" data-id="${produto.id}">Movimentar</button><button class="btn-acao" data-acao="editar" data-id="${produto.id}">Editar</button><button class="btn-acao btn-acao--perigo" data-acao="excluir" data-id="${produto.id}">Excluir</button>`}
        </td>`;
    return linha;
}

async function carregarProdutos() {
    const carregando = document.getElementById("produtos-estado-carregando");
    const vazio = document.getElementById("produtos-estado-vazio");
    const erro = document.getElementById("produtos-estado-erro");
    const tabela = document.getElementById("produtos-tabela");
    const tbody = document.getElementById("produtos-tbody");
    const contagem = document.getElementById("produtos-contagem");
    carregando.hidden = false; vazio.hidden = true; erro.hidden = true; tabela.hidden = true; tbody.innerHTML = "";
    try {
        const resposta = await fetch("/produtos", { headers: { Authorization: `Bearer ${token}` } });
        if (tratarBloqueioOuDeslogado(resposta)) return;
        if (!resposta.ok) throw new Error("Falha ao buscar produtos");
        const produtos = await resposta.json();
        produtosCache = produtos;
        carregando.hidden = true;
        if (!produtos.length) {
            vazio.hidden = false;
            contagem.textContent = "Nenhum produto cadastrado";
            return;
        }
        produtos.forEach(produto => tbody.appendChild(criarLinhaProduto(produto)));
        tbody.querySelectorAll(".stock-table__acoes").forEach(celula => { celula.hidden = planoVencido; });
        tabela.hidden = false;
        contagem.textContent = produtos.length === 1 ? "1 produto cadastrado" : `${produtos.length} produtos cadastrados`;
    } catch (falha) {
        carregando.hidden = true;
        erro.hidden = false;
    }
}

const overlay = document.getElementById("modal-overlay");
const form = document.getElementById("produto-form");
const formErro = document.getElementById("produto-form-error");
const selectCategoria = document.getElementById("produto-categoria");
const modalTitulo = document.getElementById("modal-titulo");
const botaoSalvar = document.getElementById("salvar-produto-btn");
const barcodeFeedback = document.getElementById("barcode-feedback");
const barcodeManual = document.getElementById("barcode-manual");
const barcodeReaderWrap = document.getElementById("barcode-reader-wrap");
let produtoEmEdicaoId = null;
let leitorCodigo = null;
let scannerAtivo = false;

async function carregarCategoriasNoSelect(categoriaSelecionadaId) {
    try {
        const resposta = await fetch("/categorias", { headers: { Authorization: `Bearer ${token}` } });
        if (!resposta.ok) return;
        const categorias = await resposta.json();
        selectCategoria.innerHTML = '<option value="">Sem categoria</option>';
        categorias.forEach(categoria => {
            const opcao = document.createElement("option");
            opcao.value = categoria.id;
            opcao.textContent = categoria.nome;
            if (categoriaSelecionadaId && categoria.id === categoriaSelecionadaId) opcao.selected = true;
            selectCategoria.appendChild(opcao);
        });
    } catch (_) {}
}

function abrirModalNovoProduto() {
    produtoEmEdicaoId = null;
    formErro.hidden = true;
    form.reset();
    barcodeFeedback.textContent = "";
    barcodeReaderWrap.hidden = true;
    modalTitulo.textContent = "Novo produto";
    botaoSalvar.textContent = "Salvar produto";
    carregarCategoriasNoSelect(null);
    overlay.classList.add("is-open");
}

function abrirModalEditarProduto(produto) {
    produtoEmEdicaoId = produto.id;
    formErro.hidden = true;
    barcodeFeedback.textContent = "";
    modalTitulo.textContent = "Editar produto";
    botaoSalvar.textContent = "Salvar alterações";
    document.getElementById("produto-nome").value = produto.nome;
    document.getElementById("produto-sku").value = produto.sku || "";
    document.getElementById("produto-descricao").value = produto.descricao || "";
    document.getElementById("produto-preco-custo").value = produto.preco_custo;
    document.getElementById("produto-preco-venda").value = produto.preco_venda;
    document.getElementById("produto-estoque-minimo").value = produto.estoque_minimo;
    barcodeManual.value = produto.sku || "";
    carregarCategoriasNoSelect(produto.categoria_id);
    overlay.classList.add("is-open");
}

async function encerrarLeitor() {
    if (leitorCodigo && scannerAtivo) {
        try { await leitorCodigo.stop(); } catch (_) {}
        scannerAtivo = false;
    }
    if (leitorCodigo) {
        try { await leitorCodigo.clear(); } catch (_) {}
        leitorCodigo = null;
    }
    barcodeReaderWrap.hidden = true;
}

async function buscarCodigoBarras(codigo) {
    const numero = String(codigo || "").replace(/\D/g, "");
    barcodeFeedback.textContent = "";
    if (!/^\d{8,14}$/.test(numero)) {
        barcodeFeedback.textContent = "Digite um código numérico válido, com 8 a 14 dígitos.";
        return;
    }
    barcodeManual.value = numero;
    document.getElementById("produto-sku").value = numero;
    barcodeFeedback.textContent = "Consultando base de produtos...";
    try {
        const resposta = await fetch(`/produtos/buscar-codigo/${encodeURIComponent(numero)}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (tratarBloqueioOuDeslogado(resposta)) return;
        const dados = await resposta.json().catch(() => ({}));
        if (!resposta.ok) throw new Error(dados.detail || "Não foi possível consultar o código.");
        if (!dados.encontrado) {
            barcodeFeedback.textContent = "Código lido, mas não encontrado na base. Preencha o nome manualmente; o código já foi colocado no cadastro.";
            return;
        }
        document.getElementById("produto-nome").value = dados.nome || "";
        document.getElementById("produto-descricao").value = dados.descricao || "";
        barcodeFeedback.textContent = "Produto encontrado! Confira os dados, informe preços e estoque e salve.";
    } catch (falha) {
        barcodeFeedback.textContent = falha.message || "Falha na consulta. Você pode preencher os dados manualmente.";
    }
}

async function iniciarLeitor() {
    if (!window.Html5Qrcode) {
        barcodeFeedback.textContent = "O leitor não carregou. Atualize a página e tente novamente.";
        return;
    }
    barcodeReaderWrap.hidden = false;
    barcodeFeedback.textContent = "Solicitando acesso à câmera...";
    try {
        leitorCodigo = new Html5Qrcode("barcode-reader");
        const formatos = [
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF,
            Html5QrcodeSupportedFormats.CODE_128
        ];
        await leitorCodigo.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: { width: 280, height: 120 }, formatsToSupport: formatos },
            async (codigoLido) => {
                if (!scannerAtivo) return;
                scannerAtivo = false;
                await encerrarLeitor();
                barcodeFeedback.textContent = `Código lido: ${codigoLido}`;
                await buscarCodigoBarras(codigoLido);
            },
            () => {}
        );
        scannerAtivo = true;
        barcodeFeedback.textContent = "Aponte a câmera para o código de barras.";
    } catch (falha) {
        await encerrarLeitor();
        barcodeFeedback.textContent = "Não foi possível abrir a câmera. Verifique a permissão do navegador ou digite o código manualmente.";
    }
}

document.getElementById("abrir-leitor-btn").addEventListener("click", iniciarLeitor);
document.getElementById("fechar-leitor-btn").addEventListener("click", encerrarLeitor);
document.getElementById("buscar-codigo-btn").addEventListener("click", () => buscarCodigoBarras(barcodeManual.value));
barcodeManual.addEventListener("keydown", evento => {
    if (evento.key === "Enter") {
        evento.preventDefault();
        buscarCodigoBarras(barcodeManual.value);
    }
});

async function fecharModal() {
    await encerrarLeitor();
    overlay.classList.remove("is-open");
}
document.getElementById("abrir-modal-btn").addEventListener("click", abrirModalNovoProduto);
document.getElementById("fechar-modal-btn").addEventListener("click", fecharModal);
document.getElementById("cancelar-modal-btn").addEventListener("click", fecharModal);
overlay.addEventListener("click", evento => { if (evento.target === overlay) fecharModal(); });

form.addEventListener("submit", async evento => {
    evento.preventDefault();
    formErro.hidden = true;
    const dados = {
        nome: document.getElementById("produto-nome").value,
        sku: document.getElementById("produto-sku").value || null,
        descricao: document.getElementById("produto-descricao").value || null,
        preco_custo: parseFloat(document.getElementById("produto-preco-custo").value) || 0,
        preco_venda: parseFloat(document.getElementById("produto-preco-venda").value) || 0,
        estoque_minimo: parseInt(document.getElementById("produto-estoque-minimo").value) || 0,
        categoria_id: selectCategoria.value ? parseInt(selectCategoria.value) : null
    };
    const estaEditando = produtoEmEdicaoId !== null;
    const url = estaEditando ? `/produtos/${produtoEmEdicaoId}` : "/produtos";
    botaoSalvar.disabled = true;
    botaoSalvar.textContent = "Salvando...";
    try {
        const resposta = await fetch(url, {
            method: estaEditando ? "PUT" : "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify(dados)
        });
        if (tratarBloqueioOuDeslogado(resposta)) return;
        if (!resposta.ok) {
            const detalhe = await resposta.json().catch(() => null);
            throw new Error(detalhe?.detail || "Não foi possível salvar o produto. Confira os dados.");
        }
        await fecharModal();
        verificarPlano().then(carregarProdutos);
    } catch (falha) {
        formErro.textContent = falha.message;
        formErro.hidden = false;
    } finally {
        botaoSalvar.disabled = false;
        botaoSalvar.textContent = estaEditando ? "Salvar alterações" : "Salvar produto";
    }
});

// Movimentação de estoque
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
function fecharModalMovimentacao() { movOverlay.classList.remove("is-open"); }
document.getElementById("mov-fechar-btn").addEventListener("click", fecharModalMovimentacao);
document.getElementById("mov-cancelar-btn").addEventListener("click", fecharModalMovimentacao);
movOverlay.addEventListener("click", evento => { if (evento.target === movOverlay) fecharModalMovimentacao(); });

movForm.addEventListener("submit", async evento => {
    evento.preventDefault();
    movFormErro.hidden = true;
    const dados = {
        produto_id: produtoEmMovimentacaoId,
        tipo: document.getElementById("mov-tipo").value,
        quantidade: parseInt(document.getElementById("mov-quantidade").value),
        motivo: document.getElementById("mov-motivo").value || null
    };
    movSalvarBtn.disabled = true;
    movSalvarBtn.textContent = "Salvando...";
    try {
        const resposta = await fetch("/movimentacoes", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify(dados)
        });
        if (tratarBloqueioOuDeslogado(resposta)) return;
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

// Ações da tabela
document.getElementById("produtos-tbody").addEventListener("click", async evento => {
    const botao = evento.target.closest("button[data-acao]");
    if (!botao) return;
    const id = parseInt(botao.dataset.id);
    const produto = produtosCache.find(p => p.id === id);
    if (botao.dataset.acao === "movimentar") {
        if (produto) abrirModalMovimentacao(produto);
        return;
    }
    if (botao.dataset.acao === "editar") {
        if (produto) abrirModalEditarProduto(produto);
        return;
    }
    if (botao.dataset.acao === "excluir") {
        const nome = produto ? produto.nome : "este produto";
        if (!window.confirm(`Tem certeza que deseja excluir "${nome}"? Essa ação não pode ser desfeita.`)) return;
        try {
            const resposta = await fetch(`/produtos/${id}`, {
                method: "DELETE", headers: { Authorization: `Bearer ${token}` }
            });
            if (tratarBloqueioOuDeslogado(resposta)) return;
            if (!resposta.ok) throw new Error("Não foi possível excluir o produto.");
            carregarProdutos();
        } catch (falha) { alert(falha.message); }
    }
});

verificarPlano().then(carregarProdutos);
