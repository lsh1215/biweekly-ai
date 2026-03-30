"""Sprint 0: SmolVLA MPS load tests (TDD - written first)."""

import sys
import pytest
import torch


class TestMPSAvailability:
    """Test that MPS backend is available on this Mac."""

    def test_mps_backend_available(self):
        """MPS backend should be available on Apple Silicon."""
        assert torch.backends.mps.is_available(), "MPS backend not available"

    def test_mps_device_creation(self):
        """Should be able to create a tensor on MPS device."""
        if not torch.backends.mps.is_available():
            pytest.skip("MPS not available")
        t = torch.tensor([1.0, 2.0, 3.0], device="mps")
        assert t.device.type == "mps"
        assert t.sum().item() == 6.0


class TestSmolVLAModelLoad:
    """Test SmolVLA model loading via transformers."""

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_smolvla_policy_creates(self):
        """SmolVLA policy should be creatable from config."""
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

        config = SmolVLAConfig()
        policy = SmolVLAPolicy(config)
        assert policy is not None

        params = sum(p.numel() for p in policy.parameters()) / 1e6
        assert params > 100, f"Model too small: {params:.0f}M"

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_smolvla_model_loads_on_mps(self):
        """SmolVLA model should load and move to MPS."""
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

        config = SmolVLAConfig()
        policy = SmolVLAPolicy(config)

        if torch.backends.mps.is_available():
            policy = policy.to("mps")
            param = next(policy.parameters())
            assert param.device.type == "mps"

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_memory_usage_under_limit(self):
        """Model memory usage should be under 8GB."""
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

        config = SmolVLAConfig()
        policy = SmolVLAPolicy(config)

        param_bytes = sum(p.numel() * p.element_size() for p in policy.parameters())
        param_gb = param_bytes / (1024 ** 3)

        assert param_gb < 8.0, f"Model uses {param_gb:.2f} GB, exceeds 8GB limit"


class TestFallbackPolicy:
    """Test that fallback scripted policy works if SmolVLA fails."""

    def test_scripted_policy_returns_actions(self):
        """Scripted policy should return valid joint angles."""
        from src.executor.models.scripted_policy import ScriptedPolicy

        policy = ScriptedPolicy()
        actions = policy.predict(instruction="pick apple from shelf A")

        assert len(actions.joint_angles) == 6
        assert 0.0 <= actions.gripper <= 1.0

    def test_scripted_policy_different_instructions(self):
        """Scripted policy should handle different instructions."""
        from src.executor.models.scripted_policy import ScriptedPolicy

        policy = ScriptedPolicy()

        pick_action = policy.predict(instruction="pick apple from shelf A")
        place_action = policy.predict(instruction="place apple in collection box")

        # Actions should be different for different instructions
        assert pick_action.joint_angles != place_action.joint_angles or \
               pick_action.gripper != place_action.gripper
