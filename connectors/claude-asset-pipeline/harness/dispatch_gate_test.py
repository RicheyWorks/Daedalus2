# SPDX-License-Identifier: MIT
"""No request bytes may precede the final host authorization gate."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asset_pipeline import wire


class Connection:
    def __init__(self):self.sent=[];self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def sendall(self,payload):self.sent.append(payload)


class DispatchGateTest(unittest.TestCase):
    def test_refused_gate_closes_connection_without_dispatch(self):
        connection=Connection();receipt={};states=[]
        def refuse():raise ValueError('lease expired during preparation')
        with patch.object(wire.socket,'create_connection',return_value=connection):
            with self.assertRaises(ValueError):
                wire.call(('unused',1),'execute_python',receipt=receipt,
                          on_progress=lambda r:states.append(r['state']),before_dispatch=refuse)
        self.assertEqual(connection.sent,[])
        self.assertTrue(connection.closed)
        self.assertEqual(states,['prepared','not-dispatched'])
        self.assertEqual(receipt['state'],'not-dispatched')


if __name__=='__main__':unittest.main()
