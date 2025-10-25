import json
from typing import Dict, Any

class MessageDecoder:
    """
    Decodifica e valida mensagens recebidas, garantindo que sigam
    a estrutura esperada descrita em message_models.md.
    """

    def decode(self, message: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Valida a estrutura base de uma mensagem.

        Args:
            message: O dicionário da mensagem a ser decodificado.

        Returns:
            A mensagem validada se a estrutura estiver correta, None caso contrário.
        """
        required_keys = ["message_id", "timestamp", "origin_user_id", "object", "action", "payload"]

        if not all(key in message for key in required_keys):
            print(f"[Decoder] Erro: A mensagem {message.get('message_id', '')} não possui todas as chaves necessárias.")
            return None

        obj = message.get('object')
        action = message.get('action')

        print(f"[Decoder] Mensagem {obj}/{action} decodificada com sucesso.")
        return message
