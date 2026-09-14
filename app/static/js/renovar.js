/**
 * Lógica compartilhada pelas páginas /renovar e /assinatura.
 *
 * As duas páginas têm o mesmo botão de pagamento (id="renovar-btn"),
 * então usam o mesmo script. A página /renovar também tem um link de
 * logout (id="sair-link"); a /assinatura não tem, então esse trecho
 * é escrito de forma defensiva (só age se o elemento existir).
 */

const token = sessionStorage.getItem("stockhub_token");

if (!token) {
    window.location.href = "/login";
}

const linkSair = document.getElementById("sair-link");
if (linkSair) {
    linkSair.addEventListener("click", (evento) => {
        evento.preventDefault();
        sessionStorage.removeItem("stockhub_token");
        window.location.href = "/login";
    });
}

document.getElementById("renovar-btn").addEventListener("click", async () => {
    const botao = document.getElementById("renovar-btn");
    const erro = document.getElementById("renovar-erro");
    const textoOriginal = botao.textContent;

    erro.hidden = true;
    botao.disabled = true;
    botao.textContent = "Gerando link de pagamento...";

    try {
        const resposta = await fetch("/assinatura/upgrade", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível gerar o link de pagamento. Tente novamente.");
        }

        const dados = await resposta.json();
        window.location.href = dados.url;
    } catch (falha) {
        erro.textContent = falha.message;
        erro.hidden = false;
        botao.disabled = false;
        botao.textContent = textoOriginal;
    }
});