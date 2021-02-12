# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from typing import Set
import unittest
from unittest.mock import Mock

from eduvpn.state_machine import (
    ENTER, EXIT, StateMachine, transition_callback, transition_edge_callback,
    InvalidStateTransition)
from tests.mock_config import mock_config_dict


class StateMachineTests(unittest.TestCase):
    def test_state_transition(self):
        initial_state = Mock()
        final_state = object()
        initial_state.perform_the_transition.return_value = final_state

        sm = StateMachine(initial_state)
        self.assertIs(sm.state, initial_state)

        sm.transition('perform_the_transition', 1, x=2)
        self.assertIs(sm.state, final_state)
        initial_state.perform_the_transition.assert_called_once_with(1, x=2)

    def test_generic_callback(self):
        initial_state = Mock()
        final_state = object()
        initial_state.perform_the_transition.return_value = final_state
        callback = Mock()

        sm = StateMachine(initial_state)
        sm.register_generic_callback(callback)
        sm.transition('perform_the_transition')
        callback.assert_called_once_with(initial_state, final_state)

    def test_edge_callback(self):
        class InitialState:
            def perform_the_transition(self):
                return final_state

        class FinalState:
            pass

        class OtherState:
            pass

        initial_state = InitialState()
        final_state = FinalState()

        enter_initial_callback = Mock()
        exit_initial_callback = Mock()
        enter_final_callback = Mock()
        exit_final_callback = Mock()
        other_callback = Mock()

        sm = StateMachine(initial_state)
        sm.register_edge_callback(InitialState, ENTER, enter_initial_callback)
        sm.register_edge_callback(InitialState, EXIT, exit_initial_callback)
        sm.register_edge_callback(FinalState, ENTER, enter_final_callback)
        sm.register_edge_callback(FinalState, EXIT, exit_final_callback)
        sm.register_edge_callback(OtherState, ENTER, other_callback)
        sm.register_edge_callback(OtherState, EXIT, other_callback)

        sm.transition('perform_the_transition')
        exit_initial_callback.assert_called_once_with(
            initial_state, final_state)
        enter_final_callback.assert_called_once_with(
            initial_state, final_state)

        enter_initial_callback.assert_not_called()
        exit_final_callback.assert_not_called()
        other_callback.assert_not_called()

    def test_connect_object_callbacks(self):
        class BaseState:
            pass

        class InitialState(BaseState):
            def perform_the_transition(self):
                return final_state

        class FinalState(BaseState):
            pass

        class OtherBaseState:
            pass

        initial_state = InitialState()
        final_state = FinalState()

        class Connector:
            def __init__(self):
                self.calls: Set[str] = set()

            @transition_callback(BaseState)
            def any(self, old, new):
                self.calls.add(('any', old, new))

            @transition_edge_callback(ENTER, InitialState)
            def enter_initial(self, old, new):
                self.calls.add(('enter_initial', old, new))

            @transition_edge_callback(EXIT, InitialState)
            def exit_initial(self, old, new):
                self.calls.add(('exit_initial', old, new))

            @transition_callback(OtherBaseState)
            def other(self, old, new):
                # This callback targets another state machine.
                raise AssertionError

        connector = Connector()
        sm = StateMachine(initial_state)
        sm.connect_object_callbacks(connector, BaseState)
        sm.transition('perform_the_transition')
        self.assertEqual(connector.calls, {
            ('any', initial_state, final_state),
            ('exit_initial', initial_state, final_state),
        })
