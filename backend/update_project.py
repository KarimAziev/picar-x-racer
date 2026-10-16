"""Update a checkout and its dependencies while its systemd service is stopped."""

import argparse
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal


ServiceScope = Literal["auto", "system", "user", "none"]


class ProjectUpdater:
    def __init__(
        self,
        root: Path,
        *,
        service_name: str = "picar_x_racer.service",
        service_scope: ServiceScope = "auto",
        make: str = "make",
        backend_dir: str = "backend",
        frontend_dir: str = "frontend",
        venv_dir: str = "backend/.venv",
        log_level: str = "",
    ) -> None:
        self.root = root.resolve()
        self.service_name = service_name
        self.service_scope = service_scope
        self.make = make
        self.backend_dir = backend_dir
        self.make_variables = [
            f"BACKEND_DIR={backend_dir}",
            f"FRONTEND_DIR={frontend_dir}",
            f"VENV_DIR={venv_dir}",
            f"LOG_LEVEL={log_level}",
        ]
        self.systemctl = ["systemctl"]
        if service_scope == "user":
            self.systemctl.append("--user")

    def run(
        self, args: list[str], *, capture: bool = False, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, cwd=self.root, text=True, capture_output=capture, check=check
        )

    def preflight(self) -> None:
        for command in ("git", "npm", "bash", self.make):
            if shutil.which(command) is None:
                raise RuntimeError(f"Required command is unavailable: {command}")
        if self.service_name.startswith("-") or not self.service_name.endswith(
            ".service"
        ):
            raise ValueError("SERVICE_NAME must name a .service unit")
        top = self.run(["git", "rev-parse", "--show-toplevel"], capture=True).stdout
        if Path(top.strip()).resolve() != self.root:
            raise RuntimeError("The project directory must be the Git checkout root")
        branch = self.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            capture=True,
            check=False,
        )
        if branch.returncode != 0:
            raise RuntimeError("Check out a branch with an upstream before updating")
        upstream = self.run(
            ["git", "rev-parse", "--verify", "@{upstream}"], capture=True, check=False
        )
        if upstream.returncode != 0:
            raise RuntimeError("The current branch needs an upstream before updating")
        changes = self.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], capture=True
        ).stdout
        if changes.strip():
            raise RuntimeError(
                "Tracked files have local or staged changes. Commit or stash them "
                "before updating; the checkout has not been modified."
            )

    def service_properties(self) -> dict[str, str]:
        result = self.run(
            [
                *self.systemctl,
                "show",
                "--property=LoadState,ActiveState,Result,WorkingDirectory",
                self.service_name,
            ],
            capture=True,
            check=False,
        )
        properties = dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )
        if properties.get("LoadState") == "not-found":
            return properties
        if result.returncode != 0 or not properties.get("LoadState"):
            raise RuntimeError(
                "Cannot determine service state: "
                + (result.stderr.strip() or "systemctl returned no LoadState")
                + ". Use SERVICE_SCOPE=none only for a foreground installation."
            )
        return properties

    def service_action(self, action: str) -> None:
        prefix = []
        if "--user" not in self.systemctl and os.geteuid() != 0:
            prefix = ["sudo"]
        self.run([*prefix, *self.systemctl, action, self.service_name])

    def stop_service(self) -> bool:
        if self.service_scope == "none":
            return False
        if shutil.which("systemctl") is None:
            if self.service_scope == "auto":
                return False
            raise RuntimeError("systemctl is unavailable")
        state = self.service_properties()
        if state["LoadState"] == "not-found" and self.service_scope == "auto":
            self.systemctl = ["systemctl", "--user"]
            state = self.service_properties()
        if state["LoadState"] == "not-found":
            return False
        if state["LoadState"] != "loaded":
            raise RuntimeError(
                f"Service cannot be updated: LoadState={state['LoadState']}"
            )
        working_directory = state.get("WorkingDirectory")
        if (
            working_directory
            and Path(working_directory).resolve()
            != (self.root / self.backend_dir).resolve()
        ):
            raise RuntimeError(
                "The service's WorkingDirectory points to a different checkout"
            )
        if state.get("ActiveState") not in ("inactive", "failed"):
            print(f"Stopping {self.service_name}...", flush=True)
            self.service_action("stop")
            state = self.service_properties()
            if (
                state.get("ActiveState") != "inactive"
                or state.get("Result") != "success"
            ):
                raise RuntimeError(f"Service did not stop cleanly: {state}")
        return True

    def update(self) -> None:
        self.preflight()
        lock_path = self.run(
            ["git", "rev-parse", "--git-path", "picar-x-racer-update.lock"],
            capture=True,
        ).stdout.strip()
        with (self.root / lock_path).open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(
                    "Another updater or its foreground application is running"
                ) from error
            has_service = self.stop_service()
            try:
                print("Pulling the current branch with --ff-only...", flush=True)
                self.run(["git", "pull", "--ff-only", "--no-rebase"])
                # Each invocation reads the Makefile from the updated checkout.
                for target in ("backend-deps-sync", "frontend-ci", "frontend-build"):
                    self.run([self.make, target, *self.make_variables])
            except BaseException:
                if has_service:
                    print(
                        f"Update failed; {self.service_name} remains stopped. "
                        "Resolve the error and rerun make update.",
                        file=sys.stderr,
                    )
                raise
            if has_service:
                print(f"Starting {self.service_name}...", flush=True)
                self.service_action("start")
                state = self.service_properties()
                if state.get("ActiveState") != "active":
                    raise RuntimeError(f"Service is not active after startup: {state}")
                print(f"Update complete; {self.service_name} is active.", flush=True)
            else:
                print(
                    "No selected service is installed; starting in the foreground.",
                    flush=True,
                )
                self.run([self.make, "backend-run", *self.make_variables])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-name", default="picar_x_racer.service")
    parser.add_argument(
        "--service-scope",
        choices=("auto", "system", "user", "none"),
        default="auto",
        help="auto looks for a system service, then a user service; none selects foreground operation",
    )
    parser.add_argument("--make", default="make")
    parser.add_argument("--backend-dir", default="backend")
    parser.add_argument("--frontend-dir", default="frontend")
    parser.add_argument("--venv-dir", default="backend/.venv")
    parser.add_argument("--log-level", default="")
    args = parser.parse_args()
    try:
        ProjectUpdater(Path(__file__).resolve().parent.parent, **vars(args)).update()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Update failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
