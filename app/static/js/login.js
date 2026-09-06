/**
 * Lógica da tela de login.
 *
 * A rota POST /auth/login espera dados de formulário (não JSON),
 * porque foi construída com OAuth2PasswordRequestForm no FastAPI.
 * Por isso usamos URLSearchParams em vez de JSON.stringify.
 */
document.getElementById("login-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;
    const botao = document.getElementById("submit-btn");
    const erro = document.getElementById("form-error");

    erro.hidden = true;
    botao.disabled = true;
    botao.textContent = "Entrando...";

    try {
        const corpo = new URLSearchParams();
        corpo.append("username", email);
        corpo.append("password", senha);

        const resposta = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: corpo,
        });

        if (!resposta.ok) {
            throw new Error("E-mail ou senha inválidos.");
        }

        const dados = await resposta.json();

        // Guarda o token para as próximas telas usarem nas chamadas à API.
        sessionStorage.setItem("Stokfy_token", dados.access_token);

        window.location.href = "/painel";
    } catch (falha) {
        erro.textContent = falha.message || "Não foi possível entrar. Tente novamente.";
        erro.hidden = false;
        botao.disabled = false;
        botao.textContent = "Entrar";
    }
});