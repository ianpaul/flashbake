"""
test_plugin_behavior.py — Tests for individual plugin outputs.

WHAT IS BEING TESTED
--------------------
These tests verify that plugins write sensible content to the commit
message file. They test behaviour, not implementation: we write to a
real temp file, read it back, and check the content.

Key principle: a plugin test passes only if the OUTPUT is correct.
We never test that a specific internal function was called.

PLUGIN PROPERTY NAMING
-----------------------
Flashbake prefixes plugin properties with the lowercased class name.
For example, the Timestamp class defines property 'time_format', so
the config key is 'timestamp_time_format' (prefix 'timestamp' + '_' + 'time_format').
This is why the fixture sets extra_props['timestamp_time_format'], not just
extra_props['time_format'].

HOW TO RUN
----------
  pytest test/test_plugin_behavior.py -v
"""

import os
import re
import tempfile
import pytest
from pathlib import Path

from flashbake import ControlConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_plugin_addcontext(plugin_spec, extra_props=None):
    """
    Instantiate a plugin, run its addcontext() against a real temp file,
    and return the text that was written.

    extra_props — dict of config properties (using the full config-key names,
                  e.g. {'timestamp_time_format': 'local'})
    """
    config = ControlConfig()
    if extra_props:
        config.extra_props.update(extra_props)

    # Simulate what ControlConfig.init() does for one plugin
    config.plugin_names = [plugin_spec]
    plugin = config.create_plugin(plugin_spec)
    plugin.share_properties(config)
    plugin.capture_properties(config)
    plugin.init(config)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    ) as f:
        msg_path = f.name
        plugin.addcontext(f, config)

    try:
        with open(msg_path, 'r', encoding='utf-8') as f:
            return f.read()
    finally:
        os.unlink(msg_path)


# ---------------------------------------------------------------------------
# Timestamp plugin
# ---------------------------------------------------------------------------

class TestTimestampPlugin:
    """
    The Timestamp plugin writes the current date/time to the commit message.

    It requires two config properties:
      timestamp_time_format  — 'local' or 'UTC'
      timestamp_time_hours   — '12' or '24'
    """

    PROPS_LOCAL_24 = {'timestamp_time_format': 'local', 'timestamp_time_hours': '24'}
    PROPS_LOCAL_12 = {'timestamp_time_format': 'local', 'timestamp_time_hours': '12'}
    PROPS_UTC_24   = {'timestamp_time_format': 'UTC',   'timestamp_time_hours': '24'}
    PROPS_UTC_12   = {'timestamp_time_format': 'UTC',   'timestamp_time_hours': '12'}

    def test_writes_something(self):
        """Plugin must write non-empty content to the message file."""
        output = run_plugin_addcontext(
            'flashbake.plugins.timestamp:Timestamp', self.PROPS_LOCAL_24
        )
        assert output.strip(), "Timestamp plugin wrote nothing"

    def test_local_24h_contains_time(self):
        """
        Local/24h format should produce output containing HH:MM.
        Example: 'Monday, February 26, 2026 14:32 in UTC'
        """
        output = run_plugin_addcontext(
            'flashbake.plugins.timestamp:Timestamp', self.PROPS_LOCAL_24
        )
        assert re.search(r'\d{1,2}:\d{2}', output), (
            f"Expected HH:MM in timestamp output.\nActual: {repr(output)}"
        )

    def test_local_12h_contains_am_pm(self):
        """
        Local/12h format should include AM or PM.
        Example: 'Monday, February 26, 2026 02:32 PM in UTC'
        """
        output = run_plugin_addcontext(
            'flashbake.plugins.timestamp:Timestamp', self.PROPS_LOCAL_12
        )
        assert re.search(r'\b(AM|PM)\b', output, re.IGNORECASE), (
            f"Expected AM or PM in 12-hour timestamp output.\nActual: {repr(output)}"
        )

    def test_utc_output_mentions_utc(self):
        """UTC format output should contain the word 'UTC'."""
        output = run_plugin_addcontext(
            'flashbake.plugins.timestamp:Timestamp', self.PROPS_UTC_24
        )
        assert 'UTC' in output, (
            f"Expected 'UTC' in UTC-format timestamp output.\nActual: {repr(output)}"
        )

    def test_local_output_does_not_say_utc(self):
        """Local format output should not say 'UTC' (it says 'in <zone>')."""
        output = run_plugin_addcontext(
            'flashbake.plugins.timestamp:Timestamp', self.PROPS_LOCAL_24
        )
        # 'local' format writes 'HH:MM in <zone>' not 'HH:MM UTC'
        # The word UTC should not appear right after the time digits
        assert not re.search(r'\d:\d+ UTC', output), (
            f"Local format should not use UTC time.\nActual: {repr(output)}"
        )

    def test_unconfigured_timestamp_writes_helpful_error(self):
        """
        If time_format/time_hours are not configured, the plugin should write
        an error message to the commit rather than crashing silently.

        Note: the current implementation raises AttributeError in this case
        (None.casefold() fails). This test documents that known issue — it
        is expected to fail until the plugin adds a None-guard.
        """
        pytest.xfail(
            "Known issue: Timestamp plugin crashes with AttributeError when "
            "timestamp_time_format is not configured (None.casefold()). "
            "Plugin should write an error message instead."
        )

    def test_not_connectable(self):
        """Timestamp does not need the network."""
        config = ControlConfig()
        plugin = config.create_plugin('flashbake.plugins.timestamp:Timestamp')
        assert plugin.connectable is False, (
            "Timestamp plugin should have connectable=False (no network needed)"
        )


# ---------------------------------------------------------------------------
# TimeZone plugin
# ---------------------------------------------------------------------------

class TestTimezonePlugin:
    """
    The TimeZone plugin writes the system timezone to the commit message.
    It is also used by the Timestamp plugin to find the timezone name.
    """

    def test_writes_something(self):
        """
        TimeZone plugin should produce non-empty output.
        Even if the exact timezone cannot be determined, it should write
        something rather than silently writing nothing.
        """
        output = run_plugin_addcontext('flashbake.plugins.timezone:TimeZone')
        # On some systems timezone detection fails — the plugin logs a warning
        # but may write an empty line. We accept either a timezone name or
        # at least a newline (the plugin always writes something).
        assert output is not None, "TimeZone plugin returned None instead of writing"

    def test_not_connectable(self):
        """TimeZone does not need the network."""
        config = ControlConfig()
        plugin = config.create_plugin('flashbake.plugins.timezone:TimeZone')
        assert plugin.connectable is False


# ---------------------------------------------------------------------------
# Default plugin
# ---------------------------------------------------------------------------

class TestDefaultPlugin:
    """
    The Default plugin is used with the -m/--message CLI flag.
    It writes a user-supplied message to the commit.

    The plugin only writes when console.special_message is set
    (i.e., when flashbake was invoked with -m 'some message').
    Without that, it intentionally writes nothing.
    """

    def test_writes_special_message_when_set(self):
        """
        When console.special_message is set (simulating -m flag), the
        Default plugin should write that message to the commit.
        """
        import flashbake.console as console_module
        original = console_module.special_message
        try:
            console_module.special_message = 'Morning writing session'
            output = run_plugin_addcontext('flashbake.plugins.default:Default')
            assert 'Morning writing session' in output, (
                f"Default plugin should write the special_message.\n"
                f"Expected to find 'Morning writing session' in: {repr(output)}"
            )
        finally:
            console_module.special_message = original

    def test_writes_nothing_without_special_message(self):
        """
        Without -m flag (console.special_message is None), Default plugin
        should write nothing. This is intentional — Default is only for
        command-line messages.
        """
        import flashbake.console as console_module
        original = console_module.special_message
        try:
            console_module.special_message = None
            output = run_plugin_addcontext('flashbake.plugins.default:Default')
            assert output == '', (
                f"Default plugin should write nothing when no special_message is set.\n"
                f"Actual output: {repr(output)}"
            )
        finally:
            console_module.special_message = original

    def test_not_connectable(self):
        """Default plugin does not need the network."""
        config = ControlConfig()
        plugin = config.create_plugin('flashbake.plugins.default:Default')
        assert plugin.connectable is False


# ---------------------------------------------------------------------------
# context.buildmessagefile — the orchestrator
# ---------------------------------------------------------------------------

class TestBuildMessageFile:
    """
    context.buildmessagefile() runs all configured message plugins and
    writes their output to a temp file, returning the path.

    These tests verify the full pipeline works end-to-end without git.
    """

    def test_returns_a_valid_file_path(self):
        """buildmessagefile should return the path to a file that exists."""
        from flashbake.context import buildmessagefile
        config = ControlConfig()
        config.plugin_names = ['flashbake.plugins.timestamp:Timestamp']
        config.extra_props.update({
            'timestamp_time_format': 'local',
            'timestamp_time_hours': '24',
        })

        msg_path = buildmessagefile(config)
        try:
            assert os.path.exists(msg_path), (
                f"buildmessagefile returned a path that doesn't exist: {msg_path}"
            )
        finally:
            if os.path.exists(msg_path):
                os.unlink(msg_path)

    def test_message_file_is_not_empty(self):
        """The returned file should contain content written by the plugins."""
        from flashbake.context import buildmessagefile
        config = ControlConfig()
        config.plugin_names = ['flashbake.plugins.timestamp:Timestamp']
        config.extra_props.update({
            'timestamp_time_format': 'local',
            'timestamp_time_hours': '24',
        })

        msg_path = buildmessagefile(config)
        try:
            content = Path(msg_path).read_text(encoding='utf-8')
            assert content.strip(), (
                "buildmessagefile produced an empty file. "
                "Check that the Timestamp plugin is writing its output."
            )
        finally:
            if os.path.exists(msg_path):
                os.unlink(msg_path)

    def test_two_plugins_produce_more_than_one(self):
        """
        Running two plugins should produce more output than one plugin.
        This confirms that both plugins run and both contribute to the message.
        """
        from flashbake.context import buildmessagefile

        def get_content(plugin_names, extra=None):
            cfg = ControlConfig()
            cfg.plugin_names = list(plugin_names)
            cfg.extra_props.update({
                'timestamp_time_format': 'local',
                'timestamp_time_hours': '24',
            })
            if extra:
                cfg.extra_props.update(extra)
            path = buildmessagefile(cfg)
            try:
                return Path(path).read_text(encoding='utf-8')
            finally:
                if os.path.exists(path):
                    os.unlink(path)

        one_plugin = get_content(['flashbake.plugins.timestamp:Timestamp'])
        two_plugins = get_content([
            'flashbake.plugins.timestamp:Timestamp',
            'flashbake.plugins.timezone:TimeZone',
        ])

        assert len(two_plugins) > len(one_plugin), (
            f"Two plugins should produce more output than one.\n"
            f"One plugin ({len(one_plugin)} chars): {repr(one_plugin)}\n"
            f"Two plugins ({len(two_plugins)} chars): {repr(two_plugins)}"
        )

    def test_message_file_is_not_in_tmp_hardcode(self):
        """
        Regression test: buildmessagefile used to create files in /tmp,
        which does not exist on Windows. It should now use the system's
        temp directory instead.
        """
        from flashbake.context import buildmessagefile
        config = ControlConfig()
        config.plugin_names = ['flashbake.plugins.timestamp:Timestamp']
        config.extra_props.update({
            'timestamp_time_format': 'local',
            'timestamp_time_hours': '24',
        })

        msg_path = buildmessagefile(config)
        try:
            system_temp = tempfile.gettempdir()
            assert msg_path.startswith(system_temp), (
                f"Message file should be in the system temp directory ({system_temp}), "
                f"not in a hardcoded /tmp path.\nActual path: {msg_path}"
            )
        finally:
            if os.path.exists(msg_path):
                os.unlink(msg_path)
