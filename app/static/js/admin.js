(() => {
    const token = sessionStorage.getItem("stockhub_token");
    const loading = document.getElementById("admin-loading");
    const denied = document.getElementById("admin-denied");
    const error = document.getElementById("admin-error");
    const content = document.getElementById("admin-content");
    const tbody = document.getElementById("contas-tbody");
    const refreshButton = document.getElementById("atualizar-btn");
    let carregando = false;

    if (!token) {
        window.location.href = "/login";
        return;
    }

    function formatarData(valor) {
        if (!valor) return "Nunca";
        const data = new Date(valor.endsWith("Z") ? valor : valor + "Z");
        if (Number.isNaN(data.getTime())) return "—";
        return data.toLocaleString("pt-BR", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit"
        });
    }

    function celula(texto, classe) {
        const td = document.createElement("td");
        if (classe) td.className = classe;
        td.textContent = texto;
        return td;
    }

    function montarTabela(contas) {
        tbody.replaceChildren();
        document.getElementById("sem-contas").hidden = contas.length !== 0;

        contas.forEach(conta => {
            const tr = document.createElement("tr");
            tr.appendChild(celula(conta.nome || "—", "admin-account-name"));
            tr.appendChild(celula(conta.email || "—"));
            tr.appendChild(celula(formatarData(conta.criado_em)));
            tr.appendChild(celula(formatarData(conta.ultima_atividade)));
            const statusCell = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = conta.online ? "admin-status admin-status--online" : "admin-status";
            badge.textContent = conta.online ? "Ativa agora" : "Inativa";
            if (!conta.ativo) {
                badge.className = "admin-status admin-status--disabled";
                badge.textContent = "Desativada";
            }
            statusCell.appendChild(badge);
            tr.appendChild(statusCell);
            tbody.appendChild(tr);
        });
    }

    async function carregarDados() {
        if (carregando) return;
        carregando = true;
        refreshButton.disabled = true;
        try {
            const resposta = await fetch("/auth/admin/visao-geral", {
                headers: { Authorization: `Bearer ${token}` },
                cache: "no-store"
            });
            if (resposta.status === 401) {
                sessionStorage.removeItem("stockhub_token");
                window.location.href = "/login";
                return;
            }
            if (resposta.status === 403) {
                loading.hidden = true;
                content.hidden = true;
                denied.hidden = false;
                return;
            }
            if (!resposta.ok) {
                const dadosErro = await resposta.json().catch(() => ({}));
                throw new Error(dadosErro.detail || "Falha ao consultar o painel.");
            }
            const dados = await resposta.json();
            document.getElementById("total-contas").textContent = dados.total_contas;
            document.getElementById("contas-ativas").textContent = dados.contas_ativas;
            montarTabela(dados.contas || []);
            document.getElementById("ultima-atualizacao").textContent =
                "Atualizado às " + new Date().toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});
            loading.hidden = true;
            denied.hidden = true;
            error.hidden = true;
            content.hidden = false;
        } catch (falha) {
            loading.hidden = true;
            error.hidden = false;
            document.getElementById("admin-error-message").textContent = falha.message;
        } finally {
            carregando = false;
            refreshButton.disabled = false;
        }
    }

    refreshButton.addEventListener("click", carregarDados);
    carregarDados();
    window.setInterval(() => {
        if (!document.hidden) carregarDados();
    }, 30000);
})();