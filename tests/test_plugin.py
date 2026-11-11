"""Tests that exercise the plugin the way Hermes loads it.

Run from the repository root:

    python3 -m unittest discover -s tests -v

The package is loaded from ``__init__.py`` with a submodule search path, which
is exactly what ``hermes_cli.plugins_loader._load_directory_module`` does, so a
broken relative import fails here rather than at install time.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "exoself_plugin", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["exoself_plugin"] = module
    spec.loader.exec_module(module)
    for name in ("cert", "temper", "prompt", "exo_tools", "hooks", "exo_cli"):
        setattr(module, name, importlib.import_module(f"exoself_plugin.{name}"))
    return module


class FakeCtx:
    """Records registrations and serves config, like PluginContext does."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}
        self.tools: dict[str, dict] = {}
        self.hooks: dict[str, list] = {}
        self.sections: dict[str, dict] = {}
        self.cli: dict[str, dict] = {}

    def get_config(self, key: str, default=None):
        return self.config.get(key, default)

    def register_tool(self, name, toolset, schema, handler, **_kw):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_hook(self, name, callback, **_kw):
        self.hooks.setdefault(name, []).append(callback)

    def register_system_prompt_section(self, id, content, *, position="after_memory", max_chars=4000):
        self.sections[id] = {"content": content, "position": position, "max_chars": max_chars}

    def register_cli_command(self, name, help, setup_fn, handler_fn=None, description=""):
        self.cli[name] = {"setup_fn": setup_fn, "handler_fn": handler_fn}


class PluginCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = tempfile.mkdtemp(prefix="exoself-home-")
        self._old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = self.home
        self.plugin = load_plugin()
        self.ctx = FakeCtx()
        self.plugin.register(self.ctx)

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self._old_home

    def born(self):
        import argparse

        args = argparse.Namespace(action="born")
        self.assertEqual(self.plugin.exo_cli.handle(args), 0)
        return self.plugin.cert.load_cert()

    def test_registration_surface(self) -> None:
        self.assertEqual(
            sorted(self.ctx.tools),
            ["exoself_record_session", "exoself_status", "exoself_temperament", "exoself_verify"],
        )
        self.assertIn("on_session_end", self.ctx.hooks)
        self.assertIn(self.plugin.prompt.SECTION_ID, self.ctx.sections)
        self.assertIn("exoself", self.ctx.cli)
        self.assertTrue(hasattr(self.plugin, "exo_cli"))
        # there is deliberately no tool that draws a seed
        self.assertFalse([n for n in self.ctx.tools if "born" in n or "draw" in n])

    def test_no_certificate_means_no_section_and_clean_tool_errors(self) -> None:
        section = self.ctx.sections[self.plugin.prompt.SECTION_ID]["content"]({})
        self.assertEqual(section, "")
        out = json.loads(self.ctx.tools["exoself_status"]["handler"]({}, **{}))
        self.assertFalse(out["ok"])

    def test_birth_is_one_draw_per_profile(self) -> None:
        cert = self.born()
        self.assertTrue(cert["id"].startswith("exo_"))
        import argparse

        self.assertEqual(self.plugin.exo_cli.handle(argparse.Namespace(action="born")), 1)
        self.assertEqual(self.plugin.cert.load_cert()["seed"], cert["seed"])

    def test_section_is_bounded_and_states_precedence(self) -> None:
        self.born()
        section = self.ctx.sections[self.plugin.prompt.SECTION_ID]["content"]({})
        self.assertIn("operating contract above wins", section)
        self.assertLessEqual(len(section), self.plugin.prompt.MAX_CHARS)
        self.assertTrue(section.startswith("# Temperament"))

    def test_same_certificate_renders_the_same_text(self) -> None:
        self.born()
        first = self.plugin.temper.snapshot()["prompt"]
        second = self.plugin.temper.snapshot()["prompt"]
        self.assertEqual(first, second)

    def test_tampered_certificate_is_refused(self) -> None:
        cert = self.born()
        cert["seed"] = "00" * 32
        self.plugin.cert.write_json(self.plugin.cert.cert_path(), cert)
        out = json.loads(self.ctx.tools["exoself_verify"]["handler"]({}, **{}))
        self.assertFalse(out["ok"])
        self.assertTrue(out["problems"])

    def test_hook_records_growth_and_respects_the_cap(self) -> None:
        self.born()
        hook = self.ctx.hooks["on_session_end"][0]
        before = self.plugin.cert.load_state()["events"]
        hook(completed=True, session_id="s1", platform="cli", turn_exit_reason="stop")
        after = self.plugin.cert.load_state()["events"]
        self.assertEqual(after, before + 1)

        hook(interrupted=True, session_id="s1", platform="cli")
        hook(failed=True, session_id="s1", platform="cli")
        self.assertEqual(self.plugin.cert.load_state()["events"], before + 1)

        for _ in range(30):
            hook(completed=True, session_id="s1", platform="cli", turn_exit_reason="stop")
        self.assertEqual(self.plugin.cert.load_state()["events"], before + 1 + 19)

    def test_recorded_event_is_persisted_without_conversation_text(self) -> None:
        self.born()
        handler = self.ctx.tools["exoself_record_session"]["handler"]
        out = json.loads(handler({"summary": "shipped the plugin", "satisfied": ["make"]}, **{}))
        self.assertTrue(out["ok"])
        state = self.plugin.cert.load_state()
        self.assertEqual(state["events"], 1)
        self.assertNotIn("shipped the plugin", json.dumps(state))


if __name__ == "__main__":
    unittest.main()
