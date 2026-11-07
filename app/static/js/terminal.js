(() => {
    const token = sessionStorage.getItem("stockhub_token");
    if (!token) {
        window.location.href = "/login";
        return;
    }

    const form = document.getElementById("terminal-form");
    const input = document.getElementById("terminal-command");
    const submit = document.getElementById("terminal-submit");
    const output = document.getElementById("terminal-output");
    const screen = document.getElementById("terminal-screen");

    document.getElementById("logout-btn").addEventListener("click", () => {
        sessionStorage.removeItem("stockhub_token");
        window.location.href = "/login";
    });

    function adicionarLinha(texto, classe) {
        const linha = document.createElement("p");
        linha.className = `terminal-line ${classe || ""}`;
        linha.textContent = texto;
        output.appendChild(linha);
        screen.scrollTop = screen.scrollHeight;
    }

    async function verificarPlano() {
        try {
            const resposta = await fetch("/auth/me", {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (resposta.status === 401) {
                sessionStorage.removeItem("stockhub_token");
                window.location.href = "/login";
                return;
            }
            if (!resposta.ok) return;
            const loja = await resposta.json();
            if (loja.plano === "plus" && !loja.plano_vencido) {
                document.getElementById("status-plano-container").innerHTML =
                    '<span class="badge-plus">★ Plano Plus</span>';
            }
            if (loja.plano_vencido) {
                document.getElementById("plano-vencido-aviso").hidden = false;
                input.disabled = true;
                submit.disabled = true;
                input.placeholder = "Renove seu plano para movimentar o estoque";
            }
        } catch (erro) {
            console.warn("Não foi possível verificar o plano.", erro);
        }
    }

    document.querySelectorAll(".terminal-example").forEach((botao) => {
        botao.addEventListener("click", () => {
            input.value = botao.dataset.command;
            input.focus();
        });
    });

    form.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const comando = input.value.trim();
        if (!comando || submit.disabled) return;

        adicionarLinha(`loja@stokfy:~$ ${comando}`, "terminal-line--command");
        submit.disabled = true;
        submit.textContent = "Executando...";
        input.disabled = true;

        try {
            const resposta = await fetch("/movimentacoes/terminal", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ comando })
            });

            const dados = await resposta.json().catch(() => ({}));
            if (resposta.status === 401) {
                sessionStorage.removeItem("stockhub_token");
                window.location.href = "/login";
                return;
            }
            if (resposta.status === 402) {
                window.location.href = "/renovar";
                return;
            }
            if (!resposta.ok) {
                throw new Error(dados.detail || "Não foi possível executar o comando.");
            }

            const sinal = dados.tipo === "entrada" ? "+" : "−";
            adicionarLinha(
                `✓ ${dados.mensagem}\nProduto: ${dados.produto_nome}\nQuantidade: ${sinal}${dados.quantidade} unidade(s)\nEstoque anterior: ${dados.estoque_anterior}\nEstoque atual: ${dados.estoque_atual}\nMovimentação #${dados.movimentacao_id}`,
                "terminal-line--success"
            );
            input.value = "";
        } catch (erro) {
            adicionarLinha(`✕ ${erro.message}`, "terminal-line--error");
        } finally {
            submit.disabled = false;
            submit.innerHTML = 'Executar <span>↵</span>';
            input.disabled = false;
            input.focus();
            screen.scrollTop = screen.scrollHeight;
        }
    });

    verificarPlano();
    input.focus();
})();
