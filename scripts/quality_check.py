from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def command_for_platform(command: list[str]) -> list[str]:
    if os.name == "nt" and command and command[0] == "npm":
        return ["npm.cmd", *command[1:]]
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local RaceQuant quality checks.")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()

    commands = [
        [sys.executable, "-m", "compileall", "-q", "backend", "scripts"],
    ]
    if not args.skip_tests:
        commands.append([sys.executable, "-m", "pytest"])
    if not args.skip_frontend:
        commands.extend(
            [
                ["npm", "run", "lint", "--prefix", "frontend"],
                ["npm", "run", "build", "--prefix", "frontend"],
                ["npm", "run", "smoke", "--prefix", "frontend"],
            ]
        )

    for command in commands:
        print(f"+ {' '.join(command)}")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "backend")
        completed = subprocess.run(command_for_platform(command), cwd=ROOT, env=env, check=False)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
