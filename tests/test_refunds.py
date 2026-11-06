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

    def test_runtime_uses_communication_when_router_skips_it(self):
        router = module.build_orchestrator_agent(*[Mock() for _ in range(4)])
        communicate = router.tool_registry.registry['route_to_communication_agent']._tool_func
        with patch.object(module, '_read_workflow_state', return_value={'customer_id': 'C1', 'version': 0}), \
             patch.object(module, '_update_workflow_state', return_value={}), \
             patch.object(router.tool_registry.registry['route_to_communication_agent'], '_tool_func', wraps=communicate) as route:
            result = module._ensure_communication(router, 'session', 'C1', 'request')
        self.assertIsInstance(result, str)
        route.assert_called_once_with('session', 'C1', 'request')

    def test_communication_routes_missing_workers_in_order(self):
        workers = [Mock(return_value=name) for name in ('inventory', 'refund', 'policy', 'communication')]
        router = module.build_orchestrator_agent(*workers)
        communicate = router.tool_registry.registry['route_to_communication_agent']._tool_func
        state = {'customer_id': 'C1', 'version': 0}
        calls = []

        def update(session, values, version):
            state.update(values)
            state['version'] += 1
            calls.append(next(iter(values)))
            return state

        with patch.object(module, '_read_workflow_state', side_effect=lambda session: state), \
             patch.object(module, '_update_workflow_state', side_effect=update):
            communicate('session', 'C1', 'What is the status of order O1?')
        self.assertEqual(calls, ['inventory_agent', 'refund_agent', 'communication_agent'])
        workers[2].assert_not_called()

    def test_account_question_does_not_route_to_policy(self):
        self.assertEqual(module._required_routes('What is my account tier?'), ('inventory_agent',))
        self.assertEqual(module._required_routes('What is the warranty policy?'), ('policy_agent',))
        self.assertEqual(module._required_routes('What is the return window for Standard customers?'), ('policy_agent',))
        self.assertEqual(module._required_routes('What is 5 times $29.99 with 10% off?'), ())

    def test_communication_repairs_early_model_response(self):
        router = module.build_orchestrator_agent(*[Mock() for _ in range(4)])
        state = {'customer_id': 'C1', 'version': 1, 'communication_agent': 'premature'}
        route = router.tool_registry.registry['route_to_communication_agent']
        with patch.object(module, '_read_workflow_state', return_value=state), \
             patch.object(route, '_tool_func', return_value='corrected') as communicate:
            result = module._ensure_communication(router, 'session', 'C1', 'Where is order O1?')
        self.assertEqual(result, 'corrected')
        communicate.assert_called_once()

    def test_communication_initializes_through_router_when_model_skips_it(self):
        router = module.build_orchestrator_agent(*[Mock() for _ in range(4)])
        initialize = router.tool_registry.registry['initialize_session']
        communicate = router.tool_registry.registry['route_to_communication_agent']
        state = {'customer_id': 'C1', 'version': 0}
        with patch.object(module, '_read_workflow_state', side_effect=[None, state]), \
             patch.object(initialize, '_tool_func', return_value='initialized') as init, \
             patch.object(communicate, '_tool_func', return_value='final') as route:
            result = module._ensure_communication(router, 'session', 'C1', 'simple question')
        self.assertEqual(result, 'final')
        init.assert_called_once_with('session', 'C1')
        route.assert_called_once()


if __name__ == '__main__':
    unittest.main()
