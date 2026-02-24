# 🖨️ PrintFlow - Gestão de Produção Gráfica (SaaS Local)

![Status](https://img.shields.io/badge/Status-Em_Produção-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Mobile](https://img.shields.io/badge/Design-Mobile_First-orange)

> **Versão Atual:** v2.3 (Mobile First & WhatsApp Integration)

## 🏢 O Cenário Real (Case Study)
Este software foi desenvolvido para resolver um problema crítico na gráfica onde atuo: **a desorganização do fluxo de produção**. 

Ordens de serviço em papel se perdiam, o setor de acabamento não sabia o que a impressão tinha finalizado e o atendimento demorava para dar retorno aos clientes.

**A Solução:** Criei o PrintFlow como uma aplicação Web Local (Intranet) que roda em um servidor simples, eliminando a dependência de internet externa e centralizando a comunicação.

**Resultados Práticos:**
* **Zero perda de pedidos** desde a implantação.
* **Agilidade no Atendimento:** Com a integração de WhatsApp, o tempo de resposta ao cliente caiu drasticamente.
* **Acessibilidade:** A equipe acessa o painel pelo celular (Mobile First) sem precisar ir até um computador fixo.

---

## 🚀 Diferenciais Técnicos

### 📱 Mobile First & UX Otimizada
Diferente de sistemas administrativos comuns, o PrintFlow foi desenhado para o **uso em pé**, no chão de fábrica.
- **Touch Calibrado:** Previne arrastar cards acidentalmente durante a rolagem.
- **Modais Fullscreen:** Facilitam a edição de dados em telas pequenas de celulares.

### 🤖 Automação de Comunicação e IA (Novo)
O sistema evoluiu para uma arquitetura orientada a eventos (*Event-Driven*).
- **Notificações Inteligentes:** Ao arrastar um card no Kanban, o backend dispara um Webhook silencioso com os dados do pedido.
- **Integração n8n + Google Gemini:** Um fluxo automatizado no n8n captura o evento, utiliza a IA do Gemini (modelo 2.5 Flash) para redigir uma mensagem humanizada baseada na etapa atual de produção, e dispara a notificação via mensageria (Discord/WhatsApp), reduzindo o trabalho manual do atendimento a zero.

---

## 🛠️ Arquitetura e Tecnologias
O desafio era criar uma aplicação web robusta, mas que rodasse localmente como um executável Windows, sem configuração complexa para o usuário final.

* **Backend:** Python 3.10 + Flask (Lógica de negócio ágil).
* **Banco de Dados:** SQLite + SQLAlchemy (Portabilidade total).
* **Integrações e IA:** Webhooks nativos integrados ao n8n e Google Gemini API.
* **Frontend:** HTML5, Bootstrap 5 e **Vanilla JS** (Performance máxima sem overhead).
* **Deploy/Infra:** * **Waitress:** Servidor WSGI de produção.

* **Backend:** Python 3.10 + Flask (Lógica de negócio ágil).
* **Banco de Dados:** SQLite + SQLAlchemy (Portabilidade total, sem necessidade de servidor SQL dedicado).
* **Frontend:** HTML5, Bootstrap 5 e **Vanilla JS** (Para performance máxima sem overhead de frameworks pesados como React/Angular).
* **Deploy/Infra:** * **Waitress:** Servidor WSGI de produção (substituindo o servidor de desenvolvimento do Flask).
    * **PyInstaller:** Compilação de todo o ambiente Python em um único executável `.exe` para fácil instalação no cliente.

---

## 📦 Como Rodar (Dev Mode)

```bash
# Clone o repositório
$ git clone [https://github.com/seu-usuario/printflow.git](https://github.com/seu-usuario/printflow.git)

# Instale as dependências
$ pip install -r requirements.txt

# Execute o servidor
$ python run.py
