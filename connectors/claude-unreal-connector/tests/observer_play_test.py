# SPDX-License-Identifier: MIT
"""Fake API checks; not native proof of editor focus/input behavior."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import fake_unreal
sys.modules['unreal']=fake_unreal
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'/'ClaudeUnrealBridge'/'Content'/'Python'))
import claude_unreal_bridge as bridge


def run(params):
    generator=bridge.cmd_play(params)
    for _ in range(20):
        try:
            next(generator)
        except StopIteration as result:
            return result.value
        fake_unreal.tick()
    raise AssertionError('Play did not finish within fake ticks')


class PlayTest(unittest.TestCase):
    def setUp(self):
        fake_unreal.STATE['pie']=False
        fake_unreal.STATE['pie_wait']=0
        fake_unreal.CALLS.clear()

    def test_default_observation_uses_simulation(self):
        result=run({})
        self.assertIn('simulate',fake_unreal.CALLS)
        self.assertTrue(result['playing'])
        self.assertEqual(result['requested_mode'],'simulate')
        self.assertIsNone(result['mode_observed'])

    def test_existing_session_is_not_restarted_or_relabelled(self):
        fake_unreal.STATE['pie']=True
        result=run({})
        self.assertTrue(result['already_running'])
        self.assertFalse(result['started'])
        self.assertNotIn('simulate',fake_unreal.CALLS)

    def test_contradictory_or_coerced_modes_refused(self):
        for params in ({'mode':'play','simulate':True},{'simulate':'false'},{'mode':'other'}):
            with self.assertRaises(ValueError):run(params)


if __name__=='__main__':unittest.main()
