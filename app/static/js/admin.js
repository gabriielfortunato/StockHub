(() => {
    const token = sessionStorage.getItem("stockhub_token");
    const loading = document.getElementById("admin-loading");
    const denied = document.getElementById("admin-denied");
    const error = document.getElementById("admin-error");
    const content = document.getElementById("admin-content");
    const tbody = document.getElementById("contas-tbody");
    const refreshButton = document.getElementById("atualizar-btn");
    let carregando = false;
    let administradorId = null;
    if (!token) { window.location.href = "/login"; return; }

    function formatarData(valor) {
        if (!valor) return "—";
        const data = new Date(valor.endsWith("Z") ? valor : valor + "Z");
        return Number.isNaN(data.getTime()) ? "—" : data.toLocaleString("pt-BR", {
            day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"
        });
    }
    function celula(texto, classe) {
        const td=document.createElement("td"); if(classe)td.className=classe; td.textContent=texto; return td;
    }
    async function alterarConta(conta, alteracoes, confirmacao) {
        if (!window.confirm(confirmacao)) return;
        try {
            const resposta=await fetch("/auth/admin/contas/"+encodeURIComponent(conta.id),{
                method:"PATCH",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},
                body:JSON.stringify(alteracoes),cache:"no-store"
            });
            const dados=await resposta.json().catch(()=>({}));
            if(!resposta.ok)throw new Error(dados.detail||"Não foi possível atualizar a conta.");
            await carregarDados();
        } catch(falha){window.alert(falha.message);}
    }
    function montarTabela(contas) {
        tbody.replaceChildren();
        document.getElementById("sem-contas").hidden=contas.length!==0;
        contas.forEach(conta=>{
            const tr=document.createElement("tr");
            tr.append(celula(conta.nome||"—","admin-account-name"),celula(conta.email||"—"),
                celula(formatarData(conta.criado_em)),celula(formatarData(conta.ultima_atividade)));
            const statusCell=document.createElement("td"),badge=document.createElement("span");
            badge.className=conta.ativo?(conta.online?"admin-status admin-status--online":"admin-status"):"admin-status admin-status--disabled";
            badge.textContent=conta.ativo?(conta.online?"Ativa agora":"Ativa"):"Bloqueada";
            statusCell.append(badge);tr.append(statusCell);
            tr.append(celula((conta.plano||"gratuito").toUpperCase()+(conta.plano_expira_em?" · até "+formatarData(conta.plano_expira_em):"")));
            const actions=document.createElement("td");
            if(conta.id===administradorId){const own=document.createElement("span");own.className="admin-self-label";own.textContent="Sua conta";actions.append(own);}
            else{
                const block=document.createElement("button");block.type="button";block.className="admin-action-button";
                block.textContent=conta.ativo?"Bloquear":"Reativar";
                block.addEventListener("click",()=>alterarConta(conta,{ativo:!conta.ativo},(conta.ativo?"Bloquear":"Reativar")+" o acesso de "+conta.email+"?"));
                const plan=document.createElement("button");plan.type="button";plan.className="admin-action-button";
                plan.textContent="Alterar plano";
                plan.addEventListener("click",async()=>{
                    const novo=window.prompt("Digite GRATUITO ou PLUS para "+conta.email+":",conta.plano||"gratuito");
                    if(novo===null)return;const plano=novo.trim().toLowerCase();
                    if(!["gratuito","plus"].includes(plano)){alert("Plano inválido.");return;}
                    let expira=null;
                    if(plano==="plus"){
                        const dataExpira=window.prompt("Data de vencimento (AAAA-MM-DD). Deixe vazio para não definir vencimento:", "");
                        if(dataExpira===null)return;
                        if(dataExpira.trim()){
                            if(!/^\\d{4}-\\d{2}-\\d{2}$/.test(dataExpira.trim())){alert("Use o formato AAAA-MM-DD.");return;}
                            expira=new Date(dataExpira.trim()+"T23:59:59").toISOString();
                        }
                    }
                    await alterarConta(conta,{plano,plano_expira_em:expira}, "Alterar o plano desta conta para "+plano.toUpperCase()+"?");
                });
                const del=document.createElement("button");del.type="button";del.className="admin-delete-button";del.textContent="Excluir conta";
                del.addEventListener("click",()=>excluirConta(conta));
                actions.append(block,plan,del);
            }
            tr.append(actions);tbody.append(tr);
        });
    }
    async function excluirConta(conta) {
        const confirmacao=window.prompt("Esta ação apagará permanentemente a conta e os dados associados de "+conta.email+".\n\nDigite o e-mail completo para confirmar:");
        if(confirmacao===null)return;
        if(confirmacao.trim().toLowerCase()!==String(conta.email).toLowerCase()){alert("O e-mail não corresponde. A conta não foi excluída.");return;}
        try{
            const resposta=await fetch("/auth/admin/contas/"+encodeURIComponent(conta.id),{method:"DELETE",headers:{Authorization:"Bearer "+token},cache:"no-store"});
            const dados=await resposta.json().catch(()=>({}));
            if(!resposta.ok)throw new Error(dados.detail||"Não foi possível excluir a conta.");
            alert("Conta excluída com sucesso.");await carregarDados();
        }catch(falha){alert(falha.message);}
    }
    async function carregarDados(){
        if(carregando)return;carregando=true;refreshButton.disabled=true;
        try{
            const resposta=await fetch("/auth/admin/visao-geral",{headers:{Authorization:"Bearer "+token},cache:"no-store"});
            if(resposta.status===401){sessionStorage.removeItem("stockhub_token");location.href="/login";return;}
            if(resposta.status===403){loading.hidden=true;content.hidden=true;denied.hidden=false;return;}
            if(!resposta.ok){const d=await resposta.json().catch(()=>({}));throw new Error(d.detail||"Falha ao consultar o painel.");}
            const dados=await resposta.json();administradorId=dados.administrador_id;
            document.getElementById("total-contas").textContent=dados.total_contas;
            document.getElementById("contas-ativas").textContent=dados.contas_ativas;
            montarTabela(dados.contas||[]);
            document.getElementById("ultima-atualizacao").textContent="Atualizado às "+new Date().toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
            loading.hidden=true;denied.hidden=true;error.hidden=true;content.hidden=false;
        }catch(falha){loading.hidden=true;error.hidden=false;document.getElementById("admin-error-message").textContent=falha.message;}
        finally{carregando=false;refreshButton.disabled=false;}
    }
    refreshButton.addEventListener("click",carregarDados);carregarDados();
    window.setInterval(()=>{if(!document.hidden)carregarDados();},30000);
})();