# Placebo App – Visão Geral das Classes e Fluxos

Este README descreve, em alto nível, as principais classes do projeto, sua localização e responsabilidades.

## Organização do Projeto

- `main.py` e `placeboapp.kv`: Inicialização do aplicativo Kivy e layout base.
- `navigation_screen_manager.py`: Gerencia a navegação entre telas principais.
- `doctor_profile/`: Telas e componentes do perfil do médico/cuidador.
- `patient_profile/`: Telas e componentes do perfil do paciente.
- `backend/`: Camada de serviços e persistência local (ex.: `local_backend.py`, `database_manager.py`).
- `inbox_handler/` e `outbox_handler/`: Processamento de mensagens recebidas/enviadas.
- `auxiliary_classes/`: Utilidades auxiliares (ex.: validações e datas).
- Arquivos JSON na raiz (ex.: `patient_*.json`, `account.json`): Persistência simples local.

## Perfis e Telas (Kivy)

- `doctor_profile/doctor_screens.py`
  - `DoctorHomeScreen`: Tela principal do médico, carrega data atual e pacientes vinculados; redireciona para subtelas de conteúdo.
  - `DoctorMenuScreen`: Menu para navegar entre as diferentes seções do perfil do médico.

- `doctor_profile/doctor_patient_evolution_view.py`
  - `DoctorPatientEvolutionView`: Tela para registrar e acompanhar métricas clínicas do paciente por data.

- `doctor_profile/diagnostics_view.py`
  - Exibe, adiciona, edita e remove diagnósticos do paciente.

- `doctor_profile/events_view.py`
  - Lista e mantém eventos clínicos (consultas/exames).

- `doctor_profile/medication_view.py`
  - Gerencia medicamentos e prescrições.

- `doctor_profile/patient_management_view.py`
  - Permite convidar e desvincular pacientes.

- `doctor_profile/patient_settings_view.py`
  - Configura as métricas de acompanhamento para um paciente específico.

- `doctor_profile/doctor_settings_view.py`
  - Configurações gerais do perfil do médico (alterar senha, deletar conta).

- `patient_profile/`
  - Contém arquivos análogos aos do perfil do médico, mas com a visão e permissões do paciente.

## Backend e Persistência Local

- `backend/local_backend.py`
  - Simula o servidor. Processa mensagens da `outbox`, executa a lógica de negócio e envia respostas para a `inbox`.

- `backend/database_manager.py`
  - Abstrai as operações de leitura e escrita nos arquivos JSON, que funcionam como o banco de dados local.

- `auxiliary_classes/date_checker.py`
  - Funções utilitárias para validação e manipulação de datas.

## Arquitetura do projeto Placebo

Todas as mudanças de estado do programa Placebo são realizadas por mensagens, de cliente para servidor e vice-versa. Cada mensagem é um dicionário com estrutura pré-determinada em um json. Para manipulá-las, reservam-se duas caixas de mensagens: uma de inbox e outra de outbox. As mensagens de inbox são aquelas mensagens que devem ser executadas localmente, enviadas pelo "servidor" (em nosso caso, o "local_backend"). O outbox, por outro lado, consiste em mensagens do usuário para o backend, de modo que este se responsabilize por averiguar as validade do que foi pedido, repassando-o ou não para o banco de dados local.

- `inbox_handler/inbox_processor.py`
  - Processa mensagens recebidas na `inbox`. Essas mensagens vêm do `local_backend` e disparam atualizações na interface do usuário ou no estado local do cliente.

- `outbox_handler/outbox_processor.py`
  - Cria e enfileira mensagens na `outbox`. Essas mensagens representam ações do usuário (ex: adicionar um diagnóstico) que devem ser processadas pelo `local_backend`.

## Modelos de Mensagens

### Estrutura Base da Mensagem

Todas as mensagens compartilham uma estrutura base para garantir consistência e rastreabilidade.

```json
{
  "message_id": "msg_1716240000_user123",
  "timestamp": "2024-05-20T18:00:00Z",
  "origin_user_id": "doctor_id_10000001",
  "object": "nome_do_objeto",
  "action": "nome_da_acao",
  "payload": {
    "...": "..."
  }
}
```

*   **`message_id`**: Identificador único da mensagem.
*   **`timestamp`**: Data e hora em formato ISO 8601 (UTC) de quando a mensagem foi criada.
*   **`origin_user_id`**: ID do usuário que originou a ação.
*   **`object`**: O tipo de dado que está sendo manipulado (ex: `account`, `diagnostic`).
*   **`action`**: A operação específica a ser realizada (ex: `try_login`, `add_diagnostic`).
*   **`payload`**: Um objeto contendo os dados necessários para executar a ação.

---

### 1. Objeto: `account`

Gerencia o ciclo de vida e a autenticação das contas de usuário.

**Ações `out` (Cliente -> Servidor)**

*   **`try_login`**: Tentativa de login do usuário.
    ```json
    {
      "object": "account",
      "action": "try_login",
      "payload": { "user": "peu", "password": "123" }
    }
    ```

*   **`create_account`**: Solicitação para criar uma nova conta.
    ```json
    {
      "object": "account",
      "action": "create_account",
      "payload": {
        "profile_type": "doctor",
        "name": "Dr. House",
        "user": "dr.house",
        "password": "everybodylies"
      }
    }
    ```

*   **`change_password`**: Solicitação para alterar a senha.
    ```json
    {
      "object": "account",
      "action": "change_password",
      "payload": { "current_password": "123", "new_password": "new_secure_password" }
    }
    ```

*   **`delete_account`**: Solicitação para deletar a conta.
    ```json
    {
      "object": "account",
      "action": "delete_account",
      "payload": { "password_confirmation": "123" }
    }
    ```

**Ações `in` (Servidor -> Cliente)**

*   **`try_login_cback`**: Resposta a uma tentativa de login.
    ```json
    {
      "object": "account",
      "action": "try_login_cback",
      "payload": {
        "request_message_id": "msg_id_original_do_login",
        "executed": true,
        "user_data": {
          "id": "10000001",
          "name": "peu",
          "user": "peu",
          "profile_type": "doctor"
        }
      } 
    }
    ```

---

### 2. Objeto: `diagnostic`

Gerencia os diagnósticos de um paciente.

*   **`add_diagnostic` / `edit_diagnostic` / `delete_diagnostic`**
    ```json
    {
      "object": "diagnostic",
      "action": "add_diagnostic",
      "payload": {
        "patient_user": "paciente.a@email.com",
        "diagnostic_id": "diag1760579955",
        "cid_code": "L23.9",
        "name": "Dermatite alérgica de contato",
        "description": "Reação a níquel.",
        "date_added": "2025-10-15T22:59:15Z"
      }
    }
    ```

---

### 3. Objeto: `evolution`

Gerencia os dados de evolução das métricas de saúde de um paciente.

*   **`fill_metric`**: Preenche os valores das métricas para um dia específico.
    ```json
    {
      "object": "evolution",
      "action": "fill_metric",
      "payload": {
        "patient_id": "20000001",
        "date": "2025-09-21",
        "metrics": { "temperature": "38.0", "weight": "68.5" }
      }
    }
    ```

*   **`update_tracked_metrics`**: Define quais métricas devem ser rastreadas para um paciente.
    ```json
    {
      "object": "evolution",
      "action": "update_tracked_metrics",
      "payload": {
        "patient_id": "20000001",
        "tracked_metrics": ["temperature", "weight", "blood_pressure"]
      }
    }
    ```

---

### 4. Objeto: `event`

Gerencia exames e consultas.

*   **`add_event` / `edit_event` / `delete_event`**
    ```json
    {
      "object": "event",
      "action": "add_event",
      "payload": {
        "patient_user": "paciente.a@email.com",
        "event_id": "evt1760581248",
        "name": "Consulta com Cardiologista",
        "description": "Levar exames anteriores.",
        "date": "2028-04-21",
        "time": "10:30"
      }
    }
    ```

---

### 5. Objeto: `linking_accounts`

Gerencia o vínculo entre contas de médicos e pacientes.

**Ações `out` (Cliente -> Servidor)**

*   **`invite_patient`**: Médico convida um paciente.
    ```json
    {
      "object": "linking_accounts",
      "action": "invite_patient",
      "payload": { "patient_user_to_invite": "paciente.c@email.com" }
    }
    ```

*   **`respond_to_invitation`**: Paciente responde a um convite.
    ```json
    {
      "object": "linking_accounts",
      "action": "respond_to_invitation",
      "payload": { "doctor_id": "10000001", "response": "accept" }
    }
    ```

*   **`unlink_accounts`**: Desfaz um vínculo.
    ```json
    {
      "object": "linking_accounts",
      "action": "unlink_accounts",
      "payload": { "target_user_id": "20000002" }
    }
    ```

**Ações `in` (Servidor -> Cliente)**

*   **`establish_link`**: Servidor informa sobre um novo convite ou vínculo.
    ```json
    // Exemplo 1: Notificação para o paciente sobre um novo convite
    {
      "object": "linking_accounts",
      "action": "establish_link",
      "payload": {
        "type": "new_invitation",
        "doctor_info": { "id": "10000001", "name": "Dr. House" }
      }
    }
    // Exemplo 2: Notificação para o médico que um paciente aceitou
    {
      "object": "linking_accounts",
      "action": "establish_link",
      "payload": {
        "type": "link_established",
        "patient_info": { "id": "20000002", "name": "Paciente B" }
      }
    }
    ```

---

### 6. Objeto: `medication`

Gerencia as prescrições de medicação de um paciente.

*   **`add_med` / `edit_med` / `delete_med`**
    ```json
    {
      "object": "medication",
      "action": "add_med",
      "payload": {
        "patient_user": "paciente.a@email.com",
        "med_id": "med1760573510",
        "generic_name": "Paracetamol",
        "dosage": "750mg",
        "days_of_week": ["Todos os dias"],
        "times_of_day": ["08:00", "20:00"]
      }
    }
    ```

---

### 7. Objeto: `outbox`

Gerencia a limpeza do outbox do cliente.

**Ações `in` (Servidor -> Cliente)**

*   **`delete_from_outbox`**: O servidor instrui o cliente a remover uma mensagem do seu outbox.
    ```json
    {
      "object": "outbox",
      "action": "delete_from_outbox",
      "payload": { "message_id_to_delete": "msg_id_original" }
    }
    ```

---

### 8. Mensagens de Callback (`_cback`)

Para a maioria das ações `out`, o servidor responde com uma mensagem de confirmação (`_cback`).

**Estrutura Genérica `in` (Servidor -> Cliente)**

*   **`[action]_cback`**: Resposta genérica de confirmação.
    ```json
    {
      "object": "diagnostic",
      "action": "add_diagnostic_cback",
      "payload": {
        "request_message_id": "msg_id_da_acao_original",
        "executed": true,
        "reason": "Motivo da falha (se executed for false)."
      }
    }
    ```
