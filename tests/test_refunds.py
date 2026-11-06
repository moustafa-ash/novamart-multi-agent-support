import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import agent_orchestrator as module


class RefundTests(unittest.TestCase):
    def setUp(self):
        self.orders = Mock()
        self.customers = Mock()
        self.order = {'status': 'delivered', 'order_date': (date.today() - timedelta(days=31)).isoformat()}
        self.orders.get_item.return_value = {'Item': self.order}
        self.customers.get_item.return_value = {'Item': {'tier': 'Standard'}}
        self.db = Mock()
        self.db.Table.side_effect = lambda name: self.orders if name == 'orders' else self.customers
        self.agent = module.build_refund_agent()
        self.refund = self.agent.tool_registry.registry['initiate_refund']._tool_func

    def test_window_denies_standard_and_allows_premium(self):
        with patch.object(module, 'dynamodb', self.db), patch.dict(module.config.__dict__, {'ORDERS_TABLE': 'orders', 'CUSTOMERS_TABLE': 'customers'}):
            self.assertIn('error', self.refund('C1', 'O1', 'reason'))
            self.orders.update_item.assert_not_called()
            self.customers.get_item.return_value = {'Item': {'tier': 'Premium'}}
            self.assertIn('return_reference', self.refund('C1', 'O1', 'reason'))
            self.orders.update_item.assert_called_once()

    def test_existing_return_is_reused_and_missing_order_denied(self):
        with patch.object(module, 'dynamodb', self.db), patch.dict(module.config.__dict__, {'ORDERS_TABLE': 'orders'}):
            self.orders.get_item.return_value = {'Item': {'return_reference': 'RET-ONE'}}
            self.assertEqual(self.refund('C1', 'O1', 'again')['return_reference'], 'RET-ONE')
            self.orders.get_item.return_value = {}
            self.assertIn('error', self.refund('C2', 'O1', 'reason'))
            self.orders.update_item.assert_not_called()

    def test_orchestrator_rejects_mismatched_session_customer(self):
        workers = [Mock() for _ in range(4)]
        agent = module.build_orchestrator_agent(*workers)
        route = agent.tool_registry.registry['route_to_inventory_agent']._tool_func
        with patch.object(module, '_read_workflow_state', return_value={'customer_id': 'C1', 'version': 0}):
            with self.assertRaises(ValueError):
                route('session', 'C2', 'order status')
        workers[0].assert_not_called()


if __name__ == '__main__':
    unittest.main()
