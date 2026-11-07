const parametros = new URLSearchParams(window.location.search);
const token = parametros.get("token");
document.getElementById("redefinir-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const senha = document.getElementById("senha").value;
    const confirmacao = document.getElementById("confirmar-senha").value;
    const erro = document.getElementById("form-error");
    const sucesso = document.getElementById("form-success");
    const botao = document.getElementById("submit-btn");
    erro.hidden = true; sucesso.hidden = true;
    if (!token) { erro.textContent = "Link inválido ou incompleto. Solicite uma nova recuperação."; erro.hidden = false; return; }
    if (senha.length < 8 || !/[A-Z]/.test(senha) || !/[a-z]/.test(senha) || !/[0-9]/.test(senha)) {
        erro.textContent = "A senha precisa ter 8 caracteres, uma letra maiúscula, uma minúscula e um número."; erro.hidden = false; return;
    }
    if (senha !== confirmacao) { erro.textContent = "As senhas não coincidem."; erro.hidden = false; return; }
    botao.disabled = true; botao.textContent = "Salvando...";
    try {
        const resposta = await fetch("/auth/redefinir-senha", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({token, senha})
        });
        const dados = await resposta.json().catch(() => ({}));
        if (!resposta.ok) throw new Error(dados.detail || "Não foi possível redefinir a senha.");
        sucesso.textContent = "Senha alterada com sucesso! Redirecionando para o login...";
        sucesso.hidden = false;
        botao.textContent = "Senha redefinida";
        setTimeout(() => window.location.href = "/login", 1800);
    } catch (falha) {
        erro.textContent = falha.message || "Tente novamente mais tarde.";
        erro.hidden = false; botao.disabled = false; botao.textContent = "Redefinir senha";
    }
});
