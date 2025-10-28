# Modelos de Mensagens JSON para Comunicação

Este documento define a estrutura das mensagens JSON utilizadas para a comunicação no sistema. Cada mensagem representa uma transação ou evento.

## Estrutura Base da Mensagem

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

*   **`message_id`**: Identificador único da mensagem, pode ser uma combinação de timestamp e ID do usuário.
*   **`timestamp`**: Data e hora em formato ISO 8601 (UTC) de quando a mensagem foi criada. Essencial para sincronização.
*   **`origin_user_id`**: ID do usuário que originou a ação (seja paciente ou médico).
*   **`object`**: O tipo de dado que está sendo manipulado (ex: `account`, `diagnostic`).
*   **`action`**: A operação específica a ser realizada (ex: `try_login`, `add_diagnostic`).
*   **`payload`**: Um objeto contendo os dados necessários para executar a ação.

---

## 1. Objeto: `account`

Gerencia o ciclo de vida e a autenticação das contas de usuário.

### Ações `out` (Cliente -> Servidor)

*   **`try_login`**: Tentativa de login do usuário.
    ```json
    {
      "object": "account",
      "action": "try_login",
      "payload": {
        "user": "peu",
        "password": "123"
      }
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
        "password": "everybodylies",
        "is_also_patient": false,
        "patient_info": null
      }
    }
    ```

*   **`change_password`**: Solicitação para alterar a senha.
    ```json
    {
      "object": "account",
      "action": "change_password",
      "payload": {
        "current_password": "123",
        "new_password": "new_secure_password"
      }
    }
    ```

*   **`delete_account`**: Solicitação para deletar a conta.
    ```json
    {
      "object": "account",
      "action": "delete_account",
      "payload": {
        "password_confirmation": "123"
      }
    }
    ```

### Ações `in` (Servidor -> Cliente)

*   **`success_login`**: Resposta de login bem-sucedido.
    ```json
    {
      "object": "account",
      "action": "success_login",
      "payload": {
        "user_data": {
          "id": "10000001",
          "name": "peu",
          "user": "peu",
          "profile_type": "doctor"
        },
        "session_token": "um_token_jwt_seguro_aqui"
      }
    }
    ```

*   **`fail_login`**: Resposta de login mal-sucedido.
    ```json
    {
      "object": "account",
      "action": "fail_login",
      "payload": {
        "reason": "Usuário ou senha inválidos."
      }
    }
    ```

---

## 2. Objeto: `diagnostic`

Gerencia os diagnósticos de um paciente. As ações são as mesmas para `in` e `out`. O cliente envia (`out`) para o servidor, e o servidor envia de volta (`in`) para todos os clientes relevantes (médico e paciente) para confirmar a alteração.

*   **`add_diagnostic`**: Adiciona um novo diagnóstico.
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

*   **`edit_diagnostic`**: Edita um diagnóstico existente.
    ```json
    {
      "object": "diagnostic",
      "action": "edit_diagnostic",
      "payload": {
        "diagnostic_id": "diag1760579955",
        "cid_code": "L23.9",
        "name": "Dermatite alérgica de contato de causa não especificada",
        "description": "Reação a níquel, precisa investigar."
      }
    }
    ```

*   **`delete_diagnostic`**: Remove um diagnóstico.
    ```json
    {
      "object": "diagnostic",
      "action": "delete_diagnostic",
      "payload": {
        "diagnostic_id": "diag1760579955"
      }
    }
    ```

---

## 3. Objeto: `evolution`

Gerencia os dados de evolução das métricas de saúde de um paciente.

*   **`fill_metric`**: Preenche os valores das métricas para um dia específico.
    ```json
    {
      "object": "evolution",
      "action": "fill_metric",
      "payload": {
        "patient_id": "20000001",
        "date": "2025-09-21",
        "metrics": {
          "temperature": "38.0",
          "weight": "68.5"
        }
      }
    }
    ```

*   **`update_tracked_metrics`**: Define quais métricas devem ser rastreadas para um paciente (antes `add_metric`/`delete_metric`).
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

## 4. Objeto: `event`

Gerencia exames e consultas. A estrutura é similar à de `diagnostic`.

*   **`add_event` / `edit_event` / `delete_event`**: Ações para criar, modificar ou remover um evento.
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

## 5. Objeto: `linking_accounts`

Gerencia o vínculo entre contas de médicos e pacientes.

### Ações `out` (Cliente -> Servidor)

*   **`invite_patient`**: Médico convida um paciente.
    ```json
    {
      "object": "linking_accounts",
      "action": "invite_patient",
      "payload": {
        "patient_user_to_invite": "paciente.c@email.com"
      }
    }
    ```

*   **`respond_to_invitation`**: Paciente responde a um convite.
    ```json
    {
      "object": "linking_accounts",
      "action": "respond_to_invitation",
      "payload": {
        "doctor_id": "10000001",
        "response": "accept"
      }
    }
    ```

*   **`unlink_accounts`**: Médico ou paciente desfaz um vínculo.
    ```json
    {
      "object": "linking_accounts",
      "action": "unlink_accounts",
      "payload": {
        "target_user_id": "20000002"
      }
    }
    ```

### Ações `in` (Servidor -> Cliente)

*   **`establish_link`**: Servidor informa sobre um novo vínculo ou convite.
    ```json
    {
      "object": "linking_accounts",
      "action": "establish_link",
      "payload": {
        "type": "new_invitation",
        "doctor_info": {
          "id": "10000001",
          "name": "peu"
        }
      }
    }
    ```

---

## 6. Objeto: `medication`

Gerencia as prescrições de medicação de um paciente. A estrutura é similar à de `diagnostic`.

*   **`add_med` / `edit_med` / `delete_med`**: Ações para criar, modificar ou remover uma medicação.
    ```json
    {
      "object": "medication",
      "action": "add_med",
      "payload": {
        "patient_user": "paciente.a@email.com",
        "med_id": "med1760573510",
        "generic_name": "Paracetamol",
        "presentation": "Cápsula",
        "dosage": "750mg",
        "quantity": "1",
        "days_of_week": ["Todos os dias"],
        "times_of_day": ["08:00", "20:00"],
        "observation": "Tomar após as refeições."
      }
    }
    ```