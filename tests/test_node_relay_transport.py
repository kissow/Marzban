"""Panel relay control uses authenticated existing transports, bounded retries."""
import json
import unittest
from unittest.mock import Mock, PropertyMock, patch

import requests
import test_node_control_resilience as resilience
import test_node_device_protocol as protocol


class RelayTransportTests(unittest.TestCase):
    def test_rest_snapshot_status_paths_and_json_authentication(self):
        client = resilience.RestControlResilienceTests().client()
        item = {"node_id": 2, "listen_port": 18443, "target_address": "node2.test", "target_port": 8443}
        client.get_relay_status()
        self.assertTrue(client.session.post.call_args.args[0].endswith('/relays/status'))
        client.set_relays([item])
        call = client.session.post.call_args
        self.assertTrue(call.args[0].endswith('/relays'))
        self.assertEqual(call.kwargs['json'], {'session_id': 'existing', 'profiles': [item]})
        self.assertEqual(call.kwargs['timeout'], (10, 40))

    def test_relay_mutations_are_not_replayed_on_ambiguous_timeout(self):
        client = resilience.RestControlResilienceTests().client()
        client.session.post.side_effect = requests.ReadTimeout('ambiguous result')
        with self.assertRaises(protocol.node.NodeAPIError):
            client.set_relays([])
        client.session.post.assert_called_once()
        self.assertEqual(client._session_id, 'existing')

    def test_rpyc_client_json_contract_and_capability_failure(self):
        client = object.__new__(protocol.node.RPyCXRayNode)
        client.connection = Mock()
        item = {'node_id': 2, 'listen_port': 18443, 'target_address': 'node2.test', 'target_port': 8443}
        result = Mock(ready=True, value=json.dumps({'profiles': [item], 'running': True}))
        with patch.object(protocol.node.RPyCXRayNode, 'connected', new_callable=PropertyMock, return_value=True), patch.object(protocol.node.rpyc, 'async_', return_value=Mock(return_value=result)) as asynchronous:
            self.assertEqual(client.set_relays([item])['profiles'], [item])
            asynchronous.return_value.assert_called_once_with(json.dumps([item]))
            result.set_expiry.assert_called_once_with(40)
            result.wait.assert_called_once()
            client.connection.root.fetch_relay_status = None
            with self.assertRaises(NotImplementedError):
                client.get_relay_status()


if __name__ == '__main__':
    unittest.main()
