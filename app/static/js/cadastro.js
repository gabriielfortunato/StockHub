/**
 * Lógica da tela de cadastro de loja.
 * Depois de cadastrar com sucesso, autentica automaticamente e inicia o onboarding.
 */
const campoSenha = document.getElementById("senha");
const campoConfirmacao = document.getElementById("confirmar-senha");
function senhaValida(senha) {
    return senha.length >= 8 && /[A-Z]/.test(senha) && /[a-z]/.test(senha) && /[0-9]/.test(senha);
}
function atualizarRequisitosSenha() {
    const senha = campoSenha.value;
    const requisitos = {"req-length": senha.length >= 8,"req-upper": /[A-Z]/.test(senha),"req-lower": /[a-z]/.test(senha),"req-number": /[0-9]/.test(senha)};
    Object.entries(requisitos).forEach(([id, atendido]) => document.getElementById(id).classList.toggle("password-requirement--valid", atendido));
}
campoSenha.addEventListener("input", atualizarRequisitosSenha);
document.getElementById("cadastro-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const nome=document.getElementById("nome").value,email=document.getElementById("email").value,senha=campoSenha.value,confirmacao=campoConfirmacao.value;
    const botao=document.getElementById("submit-btn"),erro=document.getElementById("form-error");erro.hidden=true;
    if(!senhaValida(senha)){erro.textContent="A senha precisa ter pelo menos 8 caracteres, uma letra maiúscula, uma minúscula e um número.";erro.hidden=false;return;}
    if(senha!==confirmacao){erro.textContent="As senhas não coincidem. Confira os dois campos.";erro.hidden=false;return;}
    botao.disabled=true;botao.textContent="Criando conta...";
    try{
        const cadastro=await fetch("/auth/cadastro",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome,email,senha})});
        if(!cadastro.ok){const detalhe=await cadastro.json().catch(()=>null);throw new Error(detalhe?.detail||"Não foi possível criar a conta.");}
        const corpoLogin=new URLSearchParams();corpoLogin.append("username",email);corpoLogin.append("password",senha);
        const login=await fetch("/auth/login",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:corpoLogin});
        if(!login.ok){window.location.href="/login";return;}
        const dados=await login.json();sessionStorage.setItem("stockhub_token",dados.access_token);window.location.href="/boas-vindas";
    }catch(falha){erro.textContent=falha.message||"Não foi possível criar a conta. Tente novamente.";erro.hidden=false;botao.disabled=false;botao.textContent="Criar conta";}
});
