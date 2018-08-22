import mock

from tests.unit import base

from mercury_agent.procedures.stress import Stress


class TestStress(base.MercuryAgentUnitTest):

    def stress_test(self, stress_seconds=60):
        mock_stress = mock.Mock()

        Stress(stress_seconds)

        mock_stress.Stress(stress_seconds)


