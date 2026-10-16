import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestDependencySetupScript(unittest.TestCase):
    def test_dependency_sync_preserves_requirement_selected_opencv_version(
        self,
    ) -> None:
        backend = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "bin"
            binary.mkdir()
            (binary / "activate").write_text("")
            pip = binary / "pip"
            pip.write_text('#!/bin/sh\n[ "$1" = show ] && [ "$2" = opencv-python ]\n')
            pip.chmod(0o755)
            python = binary / "python"
            python.write_text("#!/bin/sh\nprintf '%s\\n' 4.11.0.86\n")
            python.chmod(0o755)
            result = subprocess.run(
                ["bash", "setup_env.sh", "--dry-run", "-s", "install_python_deps"],
                cwd=backend,
                text=True,
                capture_output=True,
                env={
                    **os.environ,
                    "VENV_DIR": str(root),
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("pip install -r requirements.txt", result.stdout)
            self.assertIn(
                "pip install --no-deps -r requirements-no-deps.txt", result.stdout
            )
            self.assertIn(
                "--force-reinstall --no-deps 'opencv-python-headless==4.11.0.86'",
                result.stdout,
            )
            self.assertNotIn("pip install platformdirs -U", result.stdout)


if __name__ == "__main__":
    unittest.main()
