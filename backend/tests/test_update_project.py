import fcntl
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from update_project import ProjectUpdater


class TestProjectUpdater(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.commands: list[list[str]] = []
        self.load_state = "loaded"
        self.user_load_state = "not-found"
        self.active_state = "active"
        self.stop_result = "success"
        self.dirty = False
        self.failed_command: list[str] = []
        self.systemctl_available = True
        self.unreachable = False
        self.service_directory = self.root / "backend"
        for patcher in (
            patch("update_project.subprocess.run", side_effect=self.run_command),
            patch("update_project.shutil.which", side_effect=self.which),
            patch("update_project.os.geteuid", return_value=1000),
            patch("builtins.print"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def which(self, command: str) -> str | None:
        if command == "systemctl" and not self.systemctl_available:
            return None
        return f"/bin/{command}"

    def run_command(
        self,
        args: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        self.assertEqual(cwd, self.root)
        self.assertTrue(text)
        self.commands.append(args)
        status, output, error = 0, "", ""
        if (
            self.failed_command
            and args[: len(self.failed_command)] == self.failed_command
        ):
            status, error = 1, "command failed"
        elif args == ["git", "rev-parse", "--show-toplevel"]:
            output = str(self.root)
        elif args[:3] == ["git", "rev-parse", "--git-path"]:
            output = "update.lock"
        elif args[:2] == ["git", "status"]:
            output = " M config.json\n" if self.dirty else ""
        elif "systemctl" in args:
            if "show" in args:
                load_state = (
                    self.user_load_state if "--user" in args else self.load_state
                )
                if self.unreachable:
                    status, error = 1, "Failed to connect to bus"
                else:
                    output = (
                        f"LoadState={load_state}\nActiveState={self.active_state}\n"
                        f"Result={self.stop_result}\nWorkingDirectory={self.service_directory}\n"
                    )
                    status = 4 if load_state == "not-found" else 0
            elif "stop" in args:
                self.active_state = "inactive"
            elif "start" in args:
                self.active_state = "active"
        if check and status:
            raise subprocess.CalledProcessError(
                status, args, output=output, stderr=error
            )
        return subprocess.CompletedProcess(args, status, stdout=output, stderr=error)

    def mutations(self) -> list[list[str]]:
        return [
            command
            for command in self.commands
            if command[:2] == ["git", "pull"]
            or command[0] == "make"
            or ("systemctl" in command and "show" not in command)
        ]

    def test_running_system_service_stops_before_pull_and_starts_after_build(
        self,
    ) -> None:
        ProjectUpdater(self.root).update()
        commands = self.mutations()
        self.assertEqual(
            commands[0], ["sudo", "systemctl", "stop", "picar_x_racer.service"]
        )
        self.assertEqual(commands[1], ["git", "pull", "--ff-only", "--no-rebase"])
        self.assertEqual(
            [command[1] for command in commands[2:-1]],
            ["backend-deps-sync", "frontend-ci", "frontend-build"],
        )
        self.assertEqual(
            commands[-1], ["sudo", "systemctl", "start", "picar_x_racer.service"]
        )

    def test_inactive_service_starts_without_redundant_stop(self) -> None:
        self.active_state = "inactive"
        ProjectUpdater(self.root).update()
        self.assertFalse(any("stop" in command for command in self.mutations()))
        self.assertEqual(self.mutations()[-1][2], "start")

    def test_absent_service_runs_in_foreground(self) -> None:
        self.load_state = "not-found"
        ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations()[-1][:2], ["make", "backend-run"])
        self.assertFalse(any("systemctl" in command for command in self.mutations()))

    def test_host_without_systemctl_runs_in_foreground(self) -> None:
        self.systemctl_available = False
        ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations()[-1][:2], ["make", "backend-run"])

    def test_user_service_does_not_use_sudo(self) -> None:
        self.user_load_state = "loaded"
        ProjectUpdater(self.root, service_scope="user").update()
        self.assertEqual(
            self.mutations()[0],
            ["systemctl", "--user", "stop", "picar_x_racer.service"],
        )
        self.assertFalse(any(command[0] == "sudo" for command in self.commands))

    def test_auto_detects_user_service_when_system_service_is_absent(self) -> None:
        self.load_state = "not-found"
        self.user_load_state = "loaded"
        ProjectUpdater(self.root).update()
        self.assertEqual(
            self.mutations()[0],
            ["systemctl", "--user", "stop", "picar_x_racer.service"],
        )
        self.assertEqual(
            self.mutations()[-1],
            ["systemctl", "--user", "start", "picar_x_racer.service"],
        )

    def test_dirty_checkout_is_rejected_before_stopping_service(self) -> None:
        self.dirty = True
        with self.assertRaisesRegex(RuntimeError, "local or staged changes"):
            ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations(), [])

    def test_unreachable_manager_does_not_fall_back_to_foreground(self) -> None:
        self.unreachable = True
        with self.assertRaisesRegex(RuntimeError, "Cannot determine service state"):
            ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations(), [])

    def test_wrong_checkout_is_rejected_before_stopping_service(self) -> None:
        self.service_directory = self.root / "another-project" / "backend"
        with self.assertRaisesRegex(RuntimeError, "different checkout"):
            ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations(), [])

    def test_stop_failure_does_not_pull_or_build(self) -> None:
        self.failed_command = ["sudo", "systemctl", "stop"]
        with self.assertRaises(subprocess.CalledProcessError):
            ProjectUpdater(self.root).update()
        self.assertEqual(len(self.mutations()), 1)

    def test_unclean_shutdown_does_not_pull_or_build(self) -> None:
        self.stop_result = "timeout"
        with self.assertRaisesRegex(RuntimeError, "did not stop cleanly"):
            ProjectUpdater(self.root).update()
        self.assertEqual(len(self.mutations()), 1)

    def test_failed_pull_install_or_build_does_not_restart(self) -> None:
        for failure in (
            ["git", "pull"],
            ["make", "backend-deps-sync"],
            ["make", "frontend-ci"],
            ["make", "frontend-build"],
        ):
            with self.subTest(command=failure):
                self.failed_command = failure
                self.commands.clear()
                self.active_state = "active"
                with self.assertRaises(subprocess.CalledProcessError):
                    ProjectUpdater(self.root).update()
                self.assertEqual(self.active_state, "inactive")
                self.assertFalse(
                    any("start" in command for command in self.mutations())
                )
                self.assertFalse(
                    any("backend-run" in command for command in self.mutations())
                )

    def test_concurrent_update_does_not_stop_service(self) -> None:
        with (self.root / "update.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, "Another updater"):
                ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations(), [])

    def test_missing_upstream_is_rejected_before_stopping_service(self) -> None:
        self.failed_command = ["git", "rev-parse", "--verify", "@{upstream}"]
        with self.assertRaisesRegex(RuntimeError, "needs an upstream"):
            ProjectUpdater(self.root).update()
        self.assertEqual(self.mutations(), [])


class TestUpdateMakefile(unittest.TestCase):
    def test_make_dry_run_never_executes_updater(self) -> None:
        project = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Makefile").write_text((project / "Makefile").read_text())
            python = root / "python3"
            python.write_text("#!/bin/sh\ntouch updater-executed\nexit 1\n")
            python.chmod(0o755)
            result = subprocess.run(
                ["make", "-n", "update"],
                cwd=root,
                text=True,
                capture_output=True,
                env={**os.environ, "PATH": f"{root}{os.pathsep}{os.environ['PATH']}"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("update_project.py", result.stdout)
            self.assertFalse((root / "updater-executed").exists())


if __name__ == "__main__":
    unittest.main()
