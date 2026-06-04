# Copyright 2026 The MathWorks, Inc.

import asyncio

from matlab_proxy.util.event_loop import get_event_loop


class TestGetEventLoop:
    def test_returns_running_loop_when_one_exists(self, mocker):
        mock_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)
        mocker.patch("asyncio.get_running_loop", return_value=mock_loop)

        result = get_event_loop()

        assert result is mock_loop

    def test_returns_existing_loop_when_no_running_loop(self, mocker):
        mock_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)
        mock_loop.is_closed.return_value = False
        mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.get_event_loop", return_value=mock_loop)

        result = get_event_loop()

        assert result is mock_loop

    def test_creates_new_loop_when_existing_loop_is_closed(self, mocker):
        closed_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)
        closed_loop.is_closed.return_value = True
        new_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)

        mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.get_event_loop", return_value=closed_loop)
        mocker.patch("asyncio.new_event_loop", return_value=new_loop)
        mock_set = mocker.patch("asyncio.set_event_loop")

        result = get_event_loop()

        assert result is new_loop
        mock_set.assert_called_once_with(new_loop)

    def test_creates_new_loop_when_get_event_loop_raises(self, mocker):
        new_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)

        mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.get_event_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.new_event_loop", return_value=new_loop)
        mock_set = mocker.patch("asyncio.set_event_loop")

        result = get_event_loop()

        assert result is new_loop
        mock_set.assert_called_once_with(new_loop)

    def test_creates_new_loop_on_windows(self, mocker):
        new_loop = mocker.MagicMock(spec=asyncio.AbstractEventLoop)

        mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.get_event_loop", side_effect=RuntimeError)
        mocker.patch("asyncio.new_event_loop", return_value=new_loop)
        mock_set = mocker.patch("asyncio.set_event_loop")
        mocker.patch("sys.platform", "win32")

        result = get_event_loop()

        assert result is new_loop
        mock_set.assert_called_once_with(new_loop)
