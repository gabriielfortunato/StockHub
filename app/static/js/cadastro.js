/**
 * Lógica da tela de cadastro de loja.
 *
 * Depois de cadastrar com sucesso, já faz o login automaticamente
 * (usando o mesmo email/senha) para levar a pessoa direto ao painel,
 * sem precisar digitar tudo de novo.
 */
document.getElementById("cadastro-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const nome = document.getElementById("nome").value;
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;
    const botao = document.getElementById("submit-btn");
    const erro = document.getElementById("form-error");

    erro.hidden = true;
    botao.disabled = true;
    botao.textContent = "Criando conta...";

    try {
        const respostaCadastro = await fetch("/auth/cadastro", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nome, email, senha }),
        });

        if (!respostaCadastro.ok) {
            const detalhe = await respostaCadastro.json().catch(() => null);
            throw new Error(detalhe?.detail || "Não foi possível criar a conta.");
        }

        // Cadastro deu certo — agora faz login automaticamente.
        const corpoLogin = new URLSearchParams();
        corpoLogin.append("username", email);
        corpoLogin.append("password", senha);

        const respostaLogin = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: corpoLogin,
        });

        if (!respostaLogin.ok) {
            window.location.href = "/login";
            return;
        }

        const dadosLogin = await respostaLogin.json();
        sessionStorage.setItem("Stokfy_token", dadosLogin.access_token);
        window.location.href = "/painel";
    } catch (falha) {
        erro.textContent = falha.message || "Não foi possível criar a conta. Tente novamente.";
        erro.hidden = false;
        botao.disabled = false;
        botao.textContent = "Criar conta";
    }
});