/**
 * Cadastro de loja. Quando a verificação de e-mail estiver configurada,
 * informa que a pessoa precisa confirmar o endereço antes de entrar.
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

        const dadosCadastro = await respostaCadastro.json().catch(() => null);
        if (!respostaCadastro.ok) {
            throw new Error(dadosCadastro?.detail || "Não foi possível criar a conta.");
        }

        if (dadosCadastro?.verification_required) {
            const formulario = document.getElementById("cadastro-form");
            formulario.innerHTML = `
                <p class="auth-form__eyebrow">Só falta confirmar</p>
                <h2 class="auth-form__title">Confira seu e-mail</h2>
                <p>Enviamos um link de confirmação para <strong>${email}</strong>.
                Abra a mensagem e confirme seu endereço para ativar sua conta.</p>
                <p class="auth-form__footer"><a href="/login">Voltar para entrar</a></p>
            `;
            return;
        }

        // Mantém o fluxo atual enquanto o envio de e-mails não estiver configurado.
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
        sessionStorage.setItem("stockhub_token", dadosLogin.access_token);
        window.location.href = "/painel";
    } catch (falha) {
        erro.textContent = falha.message || "Não foi possível criar a conta. Tente novamente.";
        erro.hidden = false;
        botao.disabled = false;
        botao.textContent = "Criar conta";
    }
});
