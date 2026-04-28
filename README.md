# PrintFlow 🖨️

Sistema de gestão estilo Kanban desenvolvido para otimizar o fluxo de produção, comunicação e controle de estoque, focado na operação do chão de fábrica (Offline-First Local).

## 🚀 Funcionalidades Principais

* **Kanban Dinâmico:** Gestão visual de OS/Pedidos com funcionalidade *Drag & Drop*, etiquetas de status personalizáveis e controle inteligente de prazos de entrega (Semáforo de atrasos).
* **Chat Corporativo Integrado:** Sistema de comunicação em tempo real com separação por:
  * Chat Global.
  * Grupos de Setores (Invisíveis no Kanban de produção).
  * Mensagens Diretas.
  * Suporte a envio de anexos e *Paste* (Ctrl+V) de prints diretamente na conversa, com opções de edição e exclusão.
* **Controle de Estoque:** Gestão centralizada de materiais, níveis mínimos e histórico completo de movimentações (Entradas/Saídas).
* **Dashboard de Produtividade:** Visão gerencial em tempo real com métricas de pedidos atrasados, status da produção e volume por setor.
* **Integração com IA e Automação:** Disparo automático de Webhooks para o n8n para atualizações de status via WhatsApp.
* **Controle de Acessos:** Sistema robusto de permissões (Administradores vs. Colaboradores), restringindo visualização de colunas e dados sensíveis.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
* **Banco de Dados:** SQLite (Focado em alta disponibilidade em rede local)
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5, SortableJS
* **Integração Externa:** n8n, WhatsApp API

## ⚙️ Instalação e Execução Local

1. Clone o repositório:
```bash
git clone [https://github.com/nunes1886/printflow2.git](https://github.com/nunes1886/printflow2.git)
cd printflow2
Crie e ative o ambiente virtual:

Bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
Instale as dependências:

Bash
pip install -r requirements.txt
Inicie o servidor:

Bash
python app.py