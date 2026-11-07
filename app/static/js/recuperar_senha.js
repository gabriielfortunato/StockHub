document.getElementById("recuperar-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const email = document.getElementById("email").value.trim();
    const botao = document.getElementById("submit-btn");
    const erro = document.getElementById("form-error");
    const sucesso = document.getElementById("form-success");
    erro.hidden = true; sucesso.hidden = true;
    botao.disabled = true; botao.textContent = "Enviando...";
    try {
        const resposta = await fetch("/auth/solicitar-recuperacao", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({email})
        });
        const dados = await resposta.json().catch(() => ({}));
        if (!resposta.ok) throw new Error(dados.detail || "Não foi possível solicitar a recuperação.");
        sucesso.textContent = dados.mensagem;
        sucesso.hidden = false;
        botao.textContent = "Solicitação enviada";
    } catch (falha) {
        erro.textContent = falha.message || "Tente novamente mais tarde.";
        erro.hidden = false; botao.disabled = false; botao.textContent = "Enviar link de recuperação";
    }
});
