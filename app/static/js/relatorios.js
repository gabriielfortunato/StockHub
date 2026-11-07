(() => {
const token=sessionStorage.getItem("stockhub_token"); if(!token){location.href="/login";return;}
const headers={Authorization:"Bearer "+token};
const moeda=v=>Number(v||0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
const data=v=>v?new Date(v.endsWith("Z")?v:v+"Z").toLocaleString("pt-BR"):"—";
async function carregar(){
 const [resumoR,alertasR,historicoR]=await Promise.all([fetch("/relatorios/resumo",{headers}),fetch("/produtos/abaixo-do-minimo",{headers}),fetch("/relatorios/movimentacoes",{headers})]);
 if([resumoR,alertasR,historicoR].some(r=>r.status===401)){sessionStorage.removeItem("stockhub_token");location.href="/login";return;}
 if(!resumoR.ok||!alertasR.ok||!historicoR.ok)throw new Error("Não foi possível carregar os relatórios.");
 const r=await resumoR.json(), alertas=await alertasR.json(), historico=await historicoR.json();
 document.getElementById("r-produtos").textContent=r.total_produtos;document.getElementById("r-unidades").textContent=r.unidades_em_estoque;document.getElementById("r-valor").textContent=moeda(r.valor_estimado_estoque);document.getElementById("r-baixo").textContent=r.produtos_baixo_estoque;
 document.getElementById("r-entradas").textContent=r.entradas_total;document.getElementById("r-saidas").textContent=r.saidas_total;
 const max=Math.max(r.entradas_total,r.saidas_total,1);document.getElementById("barra-entradas").style.width=(r.entradas_total/max*100)+"%";document.getElementById("barra-saidas").style.width=(r.saidas_total/max*100)+"%";
 const alertBox=document.getElementById("alertas-estoque");alertBox.replaceChildren();
 if(!alertas.length)alertBox.textContent="Nenhum produto precisa de reposição neste momento.";
 alertas.forEach(p=>{const div=document.createElement("div");div.className="report-alert";const nome=document.createElement("strong");nome.textContent=p.nome;const qtd=document.createElement("span");qtd.textContent=p.quantidade_atual+" un. (mínimo: "+p.estoque_minimo+")";div.append(nome,qtd);alertBox.append(div);});
 const tbody=document.getElementById("historico-tbody");tbody.replaceChildren();
 historico.forEach(m=>{const tr=document.createElement("tr");[data(m.criado_em),m.produto,m.tipo==="entrada"?"Entrada":"Saída",m.quantidade,m.motivo||"—"].forEach(v=>{const td=document.createElement("td");td.textContent=v;tr.append(td);});tbody.append(tr);});
 if(!historico.length){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=5;td.textContent="Ainda não há movimentações.";tr.append(td);tbody.append(tr);}
}
document.getElementById("atualizar-relatorios").addEventListener("click",()=>carregar().catch(e=>alert(e.message)));
document.getElementById("baixar-csv").addEventListener("click",async()=>{const r=await fetch("/relatorios/produtos.csv",{headers});if(!r.ok){alert("Não foi possível exportar os produtos.");return;}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="stokfy-produtos.csv";a.click();URL.revokeObjectURL(url);});
document.getElementById("baixar-backup").addEventListener("click",async()=>{const r=await fetch("/relatorios/backup",{headers});if(!r.ok){alert("Não foi possível gerar o backup.");return;}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="stokfy-backup.json";a.click();URL.revokeObjectURL(url);});
document.getElementById("imprimir-relatorio").addEventListener("click",()=>window.print());
document.getElementById("restaurar-backup").addEventListener("click",async()=>{const file=document.getElementById("arquivo-backup").files[0],feedback=document.getElementById("backup-feedback");if(!file){feedback.textContent="Selecione um arquivo JSON primeiro.";return;}try{const backup=JSON.parse(await file.text());if(!confirm("Os dados do backup serão adicionados aos dados atuais. Deseja continuar?"))return;const r=await fetch("/relatorios/restaurar",{method:"POST",headers:{"Content-Type":"application/json",...headers},body:JSON.stringify({backup})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha ao restaurar.");feedback.textContent=d.mensagem;await carregar();}catch(e){feedback.textContent=e.message;}});
carregar().catch(e=>{document.querySelector(".report-page").insertAdjacentText("afterbegin",e.message);});
})();