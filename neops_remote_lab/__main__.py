"""Run the remote lab server via `poetry run remote_lab` or `python -m neops_worker_sdk.testing.remote_lab`"""

from __future__ import annotations

import argparse
import logging
import logging.config
import os
from pathlib import Path
import shutil
import subprocess

import uvicorn
import yaml

from neops_remote_lab.server import app

_logger = logging.getLogger("remote-lab-server")


def setup_logging(config_path: str, log_level: str) -> None:
    """Setup logging configuration from YAML file or fallback to basic config."""
    log_config_path = Path(config_path)

    if not log_config_path.exists():
        print(f"Logging config file not found: {log_config_path}")
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), "INFO"),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        return

    try:
        with open(log_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        level = log_level.upper()
        if level != "INFO":
            # For non-INFO levels, update all logger levels.
            # For DEBUG, also switch to the debug_console handler.
            for logger_config in config.get("loggers", {}).values():
                logger_config["level"] = level
                if level == "DEBUG":
                    logger_config["handlers"] = ["debug_console"]

            # Set the root logger level, and if DEBUG, also switch to the debug_console handler.
            if "root" in config:
                config["root"]["level"] = level
                if level == "DEBUG":
                    config["root"]["handlers"] = ["debug_console"]

        logging.config.dictConfig(config)
        _logger.info("Loaded logging config from %s (level: %s)", log_config_path, level)

    except (yaml.YAMLError, IOError, KeyError) as e:
        print(f"Error processing logging config: {e}")
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), "INFO"),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


def main() -> None:
    default_logger_config_path = Path(__file__).resolve().parent.parent / "logging_config.yaml"

    parser = argparse.ArgumentParser(description="Start the Remote Lab Manager")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and stream netlab output.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--log-config",
        default=str(default_logger_config_path),
        help="Path to logging config file",
    )
    args = parser.parse_args()

    if args.debug:
        args.log_level = "DEBUG"
        _logger.info("Debug mode enabled. Netlab output will be streamed to console and loglevel set to DEBUG.")
        os.environ["NEOPS_NETLAB_STREAM_OUTPUT"] = "1"

    setup_logging(args.log_config, args.log_level)

    _logger.info("Starting Remote Lab Manager on %s:%d", args.host, args.port)

    # Pre-flight: ensure netlab CLI is available
    if shutil.which("netlab") is None:
        _logger.error("'netlab' CLI not found in PATH. The Remote Lab Manager requires Netlab to orchestrate labs.")
        _logger.error("Install Netlab: https://netlab.tools/install/ubuntu/")
        _logger.error("After installation, ensure your shell can find 'netlab' (relogin or reload your shell).")
        raise SystemExit(1)

    # Optional: verify netlab responds
    try:
        completed = subprocess.run(
            ["netlab", "version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _logger.debug("Detected %s", completed.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        _logger.error("Failed to execute 'netlab version': %s", exc)
        _logger.error("Please verify your Netlab installation: https://netlab.tools/install/ubuntu/")
        raise SystemExit(1) from exc

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        access_log=True,
        log_config=None,  # Don't let uvicorn override our logging config
    )


if __name__ == "__main__":
    main()
