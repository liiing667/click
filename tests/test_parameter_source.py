"""Unit tests for the value-source resolution layer.

These test the pure decision functions directly, without going through
the parser, so each source and precedence rule is covered in isolation.
"""

import pytest

from click._utils import FLAG_NEEDS_VALUE
from click._utils import UNSET
from click.core import _resolve_option_value_and_source
from click.core import _resolve_value_and_source
from click.core import ParameterSource


class _Supplier:
    """A value supplier that records how often it was called."""

    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


@pytest.mark.parametrize(
    ("cli_value", "envvar", "default_map", "default", "expect"),
    [
        pytest.param(
            "cli",
            "env",
            (True, "map"),
            "default",
            ("cli", ParameterSource.COMMANDLINE),
            id="commandline wins",
        ),
        pytest.param(
            UNSET,
            "env",
            (True, "map"),
            "default",
            ("env", ParameterSource.ENVIRONMENT),
            id="environment over default_map",
        ),
        pytest.param(
            UNSET,
            None,
            (True, "map"),
            "default",
            ("map", ParameterSource.DEFAULT_MAP),
            id="default_map over default",
        ),
        pytest.param(
            UNSET,
            None,
            (True, None),
            "default",
            (None, ParameterSource.DEFAULT_MAP),
            id="default_map explicit None",
        ),
        pytest.param(
            UNSET,
            None,
            (False, UNSET),
            "default",
            ("default", ParameterSource.DEFAULT),
            id="parameter default",
        ),
        pytest.param(
            UNSET,
            None,
            (False, UNSET),
            UNSET,
            (UNSET, ParameterSource.DEFAULT),
            id="no value is unset default",
        ),
    ],
)
def test_resolve_value_and_source_precedence(
    cli_value, envvar, default_map, default, expect
):
    value, source = _resolve_value_and_source(
        cli_value,
        lambda: envvar,
        lambda: default_map,
        lambda: default,
    )
    assert (value, source) == expect


def test_resolve_value_and_source_is_lazy():
    """A supplier is only called if no higher-precedence source won."""
    envvar = _Supplier("env")
    default_map = _Supplier((True, "map"))
    default = _Supplier("default")

    value, source = _resolve_value_and_source("cli", envvar, default_map, default)
    assert (value, source) == ("cli", ParameterSource.COMMANDLINE)
    assert envvar.calls == 0
    assert default_map.calls == 0
    assert default.calls == 0

    value, source = _resolve_value_and_source(UNSET, envvar, default_map, default)
    assert (value, source) == ("env", ParameterSource.ENVIRONMENT)
    assert envvar.calls == 1
    assert default_map.calls == 0
    assert default.calls == 0


def test_resolve_option_flag_needs_value_prompts():
    value, source = _resolve_option_value_and_source(
        FLAG_NEEDS_VALUE,
        ParameterSource.COMMANDLINE,
        flag_activation_value=True,
        multiple=False,
        prompt_value=lambda: "typed",
        prompt_on_default=True,
    )
    assert (value, source) == ("typed", ParameterSource.PROMPT)


def test_resolve_option_flag_needs_value_without_prompt():
    value, source = _resolve_option_value_and_source(
        FLAG_NEEDS_VALUE,
        ParameterSource.COMMANDLINE,
        flag_activation_value=True,
        multiple=False,
        prompt_value=None,
        prompt_on_default=True,
    )
    assert (value, source) == (True, ParameterSource.COMMANDLINE)


def test_resolve_option_multiple_flag_sentinels():
    value, source = _resolve_option_value_and_source(
        [FLAG_NEEDS_VALUE, "given"],
        ParameterSource.COMMANDLINE,
        flag_activation_value=True,
        multiple=True,
        prompt_value=None,
        prompt_on_default=False,
    )
    assert (value, source) == ([True, "given"], ParameterSource.COMMANDLINE)


@pytest.mark.parametrize(
    "source", [ParameterSource.DEFAULT_MAP, ParameterSource.DEFAULT]
)
def test_resolve_option_prompts_for_default_sources(source):
    value, new_source = _resolve_option_value_and_source(
        "from-default",
        source,
        flag_activation_value=True,
        multiple=False,
        prompt_value=lambda: "typed",
        prompt_on_default=True,
    )
    assert (value, new_source) == ("typed", ParameterSource.PROMPT)


def test_resolve_option_prompts_for_unset():
    value, source = _resolve_option_value_and_source(
        UNSET,
        ParameterSource.DEFAULT,
        flag_activation_value=True,
        multiple=False,
        prompt_value=lambda: "typed",
        prompt_on_default=True,
    )
    assert (value, source) == ("typed", ParameterSource.PROMPT)


@pytest.mark.parametrize(
    "source",
    [ParameterSource.PROMPT, ParameterSource.COMMANDLINE, ParameterSource.ENVIRONMENT],
)
def test_resolve_option_no_prompt_for_explicit_sources(source):
    value, new_source = _resolve_option_value_and_source(
        "explicit",
        source,
        flag_activation_value=True,
        multiple=False,
        prompt_value=lambda: "typed",
        prompt_on_default=True,
    )
    assert (value, new_source) == ("explicit", source)


def test_resolve_option_prompt_on_default_disabled():
    value, source = _resolve_option_value_and_source(
        UNSET,
        ParameterSource.DEFAULT,
        flag_activation_value=True,
        multiple=False,
        prompt_value=lambda: "typed",
        prompt_on_default=False,
    )
    assert (value, source) == (UNSET, ParameterSource.DEFAULT)
