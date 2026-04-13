"""Sprint 0.3: Validate SmolVLA model loading on MPS.

Run: python scripts/validate_smolvla.py
"""

import sys
import time
import torch


def check_mps():
    """Check MPS availability."""
    print(f"PyTorch version: {torch.__version__}")
    print(f"MPS available: {torch.backends.mps.is_available()}")
    print(f"MPS built: {torch.backends.mps.is_built()}")
    return torch.backends.mps.is_available()


def load_smolvla():
    """Attempt to load SmolVLA model."""
    print("\n--- Loading SmolVLA ---")
    start = time.time()

    try:
        from transformers import AutoModelForVision2Seq, AutoProcessor

        print("Loading processor...")
        processor = AutoProcessor.from_pretrained(
            "lerobot/smolvla_base",
            trust_remote_code=True,
        )
        print(f"Processor loaded in {time.time() - start:.1f}s")

        print("Loading model...")
        model = AutoModelForVision2Seq.from_pretrained(
            "lerobot/smolvla_base",
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )

        # Calculate model size
        param_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
        param_gb = param_bytes / (1024 ** 3)
        param_count = sum(p.numel() for p in model.parameters()) / 1e6
        print(f"Model params: {param_count:.0f}M, Size: {param_gb:.2f} GB")

        # Move to MPS if available
        if torch.backends.mps.is_available():
            print("Moving to MPS...")
            model = model.to("mps")
            device = next(model.parameters()).device
            print(f"Model on device: {device}")

        elapsed = time.time() - start
        print(f"\nSmolVLA loaded successfully in {elapsed:.1f}s")
        return True, "smolvla", param_gb

    except Exception as e:
        print(f"SmolVLA failed: {e}")
        return False, str(e), 0


def load_fallback():
    """Load scripted policy fallback."""
    print("\n--- Loading Scripted Policy Fallback ---")
    try:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
        from src.executor.models.scripted_policy import ScriptedPolicy

        policy = ScriptedPolicy()
        action = policy.predict("pick apple from shelf A")
        print(f"Scripted policy works: joints={action.joint_angles}, gripper={action.gripper}")
        return True
    except Exception as e:
        print(f"Scripted policy failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Sprint 0.3: SmolVLA MPS Validation")
    print("=" * 60)

    has_mps = check_mps()

    if not has_mps:
        print("\nWARNING: MPS not available. Will use CPU fallback.")

    success, model_name, mem_gb = load_smolvla()

    if not success:
        print("\nSmolVLA failed. Trying fallback...")
        fb = load_fallback()
        if fb:
            print("\nDECISION: Use ScriptedPolicy as fallback")
            return 0
        else:
            print("\nFATAL: All fallbacks failed")
            return 1

    print(f"\nDECISION: Use {model_name} (memory: {mem_gb:.2f} GB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
