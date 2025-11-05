"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        self.payment_id = None
        self.payment_response = {}
        super().__init__()

    def _fetch_order_total(self):
        response = requests.get(
            f'{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}',
            headers={'Content-Type': 'application/json'}
        )

        if not response.ok:
            payload = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            raise RuntimeError(f"Erreur {response.status_code} lors de la récuperation de la commande : {payload}")

        order_details = response.json() or {}
        total_raw = order_details.get('total_amount')
        if total_raw is None:
            raise RuntimeError("Impossible de determiner le total de la commande.")

        try:
            return float(total_raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Impossible de convertir le total de la commande : {total_raw}") from exc

    def _create_payment_transaction(self, total_amount):
        """Call Payments API via KrakenD to create a payment transaction."""
        payload = {
            "user_id": self.order_data.get("user_id"),
            "order_id": self.order_id,
            "total_amount": total_amount
        }

        response = requests.post(
            f'{config.API_GATEWAY_URL}/payments-api/payments',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if not response.ok:
            payload = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            raise RuntimeError(f"Erreur {response.status_code} lors de la creation du paiement : {payload}")

        data = response.json() if response.content else {}
        self.payment_response = data
        self.payment_id = data.get('payment_id')
        return data

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            self.total_amount = self._fetch_order_total()
            self._create_payment_transaction(self.total_amount)
            self.logger.debug("La création d'une transaction de paiement a réussi")
            return OrderSagaState.COMPLETED
        except Exception as exc:
            self.logger.error(f"La création d'une transaction de paiement a échoué : {exc}")
            return OrderSagaState.INCREASING_STOCK

    def rollback(self):
        """Call payment microservice to delete payment transaction"""
        # ATTENTION: Nous pourrions utiliser cette méthode si nous avions des étapes supplémentaires, mais ce n'est pas le cas actuellement, elle restera donc INUTILISÉE.
        self.logger.debug("La suppression d'une transaction de paiement a réussi")
        return OrderSagaState.INCREASING_STOCK