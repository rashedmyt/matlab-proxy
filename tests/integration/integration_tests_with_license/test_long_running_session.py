# Copyright 2026 The MathWorks, Inc.

"""
Integration test to verify that when MWI_ENABLE_LONG_RUNNING_SESSION is set,
MATLAB receives an `MWAJ` token type instead of the default `MWAS`.
"""

import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

import matlab_proxy.settings as settings
from matlab_proxy.constants import MWI_AUTH_TOKEN_NAME_FOR_HTTP
from matlab_proxy.util import system
from tests.integration.integration_tests_with_license.test_http_end_points import (
    _check_matlab_status,
)
from tests.integration.utils import integration_tests_utils as utils
from tests.utils.logging_util import create_integ_test_logger

_logger = create_integ_test_logger(__name__)

MAX_TIMEOUT = settings.get_process_startup_timeout()

MATLAB_SCRIPT_TO_VERIFY_TOKEN_TYPE = (
    Path(__file__).parent / "verify_token_type.m"
).read_text()


class LongRunningSessionMATLABServer:
    """
    Context Manager that launches matlab-proxy with MWI_ENABLE_LONG_RUNNING_SESSION
    enabled and a startup script that verifies the token type.
    """

    def __init__(self):
        self.proc = None
        self.dpipe = None
        self.mwi_app_port = None
        self.mwi_base_url = None
        self.headers = None
        self.connection_scheme = None
        self.url = None

    async def __aenter__(self):
        _logger.info(
            "Setting up MATLAB Server with MWI_ENABLE_LONG_RUNNING_SESSION enabled"
        )

        self.dpipe = os.pipe2(os.O_NONBLOCK) if system.is_linux() else os.pipe()
        self.mwi_app_port = utils.get_random_free_port()
        self.mwi_base_url = "/matlab-test"

        input_env = {
            "MWI_APP_PORT": self.mwi_app_port,
            "MWI_BASE_URL": self.mwi_base_url,
            "MWI_ENABLE_LONG_RUNNING_SESSION": "True",
            "MWI_MATLAB_STARTUP_SCRIPT": MATLAB_SCRIPT_TO_VERIFY_TOKEN_TYPE,
        }

        self.proc = await utils.start_matlab_proxy_app(
            out=self.dpipe[1], input_env=input_env
        )

        utils.wait_server_info_ready(self.mwi_app_port)
        parsed_url = urlparse(utils.get_connection_string(self.mwi_app_port))

        self.headers = {
            MWI_AUTH_TOKEN_NAME_FOR_HTTP: (
                parse_qs(parsed_url.query)[MWI_AUTH_TOKEN_NAME_FOR_HTTP][0]
                if MWI_AUTH_TOKEN_NAME_FOR_HTTP in parse_qs(parsed_url.query)
                else ""
            )
        }
        self.connection_scheme = parsed_url.scheme
        self.url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        import asyncio

        _logger.info("Tearing down MATLAB Server (long-running session test)")
        try:
            self.proc.terminate()
            await asyncio.wait_for(self.proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            self.proc.kill()
            await self.proc.wait()


@pytest.fixture
async def matlab_proxy_long_running_session_fixture():
    """Pytest fixture that yields a matlab-proxy server with long-running session enabled."""
    try:
        async with LongRunningSessionMATLABServer() as server:
            yield server
    except ProcessLookupError as e:
        _logger.debug(f"ProcessLookupError: {e}")


async def test_long_running_session_uses_mwaj_token(
    matlab_proxy_long_running_session_fixture,
):
    """Test that when MWI_ENABLE_LONG_RUNNING_SESSION is set, MATLAB is started
    with an MWAJ token and can verify this via the MathWorks auth API."""
    fixture = matlab_proxy_long_running_session_fixture

    status = _check_matlab_status(fixture, "up")
    assert status == "up", f"MATLAB did not start, status: {status}"

    read_descriptor, write_descriptor = fixture.dpipe
    number_of_bytes = 4000

    if read_descriptor:
        line = os.read(read_descriptor, number_of_bytes).decode("utf-8")
        process_logs = line.strip()

        match = re.search(
            r"The results of executing MWI_MATLAB_STARTUP_SCRIPT are stored at: \s*(.*?startup_code_output\.txt)",
            process_logs,
        )
        assert match, (
            f"Could not find startup code output file path in logs. "
            f"Log excerpt: {process_logs[:2000]}"
        )

        output_file_path = match.group(1)
        _logger.info(f"Startup code output file: {output_file_path}")

        # The startup script makes a network call to the auth service,
        # so poll for the output file to appear.
        start_time = time.time()
        while not os.path.exists(output_file_path):
            if time.time() - start_time > MAX_TIMEOUT:
                pytest.fail(
                    f"Startup code output file not found at {output_file_path} "
                    f"after {MAX_TIMEOUT}s"
                )
            time.sleep(1)

        with open(output_file_path, "r") as f:
            content = f.read()

        assert (
            "Token Type: MWAJ" in content
        ), f"Expected token type MWAJ but got: {content}"

    os.close(read_descriptor)
    os.close(write_descriptor)
