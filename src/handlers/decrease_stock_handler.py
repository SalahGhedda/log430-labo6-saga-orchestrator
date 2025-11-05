"""
Handler: decrease stock
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from logger import Logger
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class DecreaseStockHandler(Handler):
    """Handle the stock check-out of a list of items. Trigger rollback of previous steps in case of failure."""

    def __init__(self, order_item_data):
        """Constructor method"""
        self.order_item_data = order_item_data or []
        super().__init__()

    def run(self):
        """Call StoreManager to check out from stock"""
        try:
            response = requests.put(
                f'{config.API_GATEWAY_URL}/store-manager-api/stocks',
                json={
                    "items": self.order_item_data,
                    "operation": "-"
                },
                headers={'Content-Type': 'application/json'}
            )

            if response.ok:
                self.logger.debug("La sortie des articles du stock a reussi")
                return OrderSagaState.CREATING_PAYMENT

            error_payload = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            self.logger.error(f"Erreur {response.status_code} : {error_payload}")
            return OrderSagaState.CANCELLING_ORDER

        except Exception as exc:
            self.logger.error(f"La sortie des articles du stock a echoue : {exc}")
            return OrderSagaState.CANCELLING_ORDER

    def rollback(self):
        try:
            response = requests.put(
                f'{config.API_GATEWAY_URL}/store-manager-api/stocks',
                json={
                    "items": self.order_item_data,
                    "operation": "+"
                },
                headers={'Content-Type': 'application/json'}
            )

            if response.ok:
                self.logger.debug("L'entree des articles dans le stock a reussi")
            else:
                error_payload = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
                self.logger.error(f"Erreur {response.status_code} : {error_payload}")

        except Exception as e:
            self.logger.error(f"L'entree des articles dans le stock a echoue : {e}")

        return OrderSagaState.CANCELLING_ORDER
