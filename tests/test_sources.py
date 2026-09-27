"""Unit tests for the value-source resolution layer.

These exercise :func:`click._sources.resolve_value_and_source` directly,
without going through the parser, prompting, or type casting, so the
source precedence policy is pinned down in one place.
"""

import pytest

import click
from click._sources import ParameterSource
from click._sources import resolve_value_and_source
from click._utils import UNSET


def make_ctx(**kwargs):
    return click.Context(click.Command("cmd"), **kwargs)


def test_source_members_are_ordered_most_explicit_first():
    assert list(ParameterSource) == [
        ParameterSource.PROMPT,
        ParameterSource.COMMANDLINE,
        ParameterSource.ENVIRONMENT,
        ParameterSource.DEFAULT_MAP,
        ParameterSource.DEFAULT,
    ]
    assert ParameterSource.COMMANDLINE < ParameterSource.DEFAULT_MAP
    assert ParameterSource.DEFAULT > ParameterSource.ENVIRONMENT


def test_command_line_wins_over_everything(monkeypatch):
    monkeypatch.setenv("APP_PORT", "2")
    param = click.Option(["--port"], default=80, envvar="APP_PORT")
    ctx = make_ctx(default_map={"port": 3})

    value, source = resolve_value_and_source(param, ctx, {"port": 1})

    assert value == 1
    assert source is ParameterSource.COMMANDLINE


def test_envvar_wins_over_default_map_and_default(monkeypatch):
    monkeypatch.setenv("APP_PORT", "2")
    param = click.Option(["--port"], default=80, envvar="APP_PORT")
    ctx = make_ctx(default_map={"port": 3})

    value, source = resolve_value_and_source(param, ctx, {})

    assert value == "2"
    assert source is ParameterSource.ENVIRONMENT


def test_default_map_wins_over_default():
    param = click.Option(["--port"], default=80)
    ctx = make_ctx(default_map={"port": 3})

    value, source = resolve_value_and_source(param, ctx, {})

    assert value == 3
    assert source is ParameterSource.DEFAULT_MAP


def test_default_map_may_provide_none():
    param = click.Option(["--port"], default=80)
    ctx = make_ctx(default_map={"port": None})

    value, source = resolve_value_and_source(param, ctx, {})

    assert value is None
    assert source is ParameterSource.DEFAULT_MAP


def test_default_map_string_is_split_for_multi_value_parameters():
    param = click.Option(["--pair"], nargs=2)
    ctx = make_ctx(default_map={"pair": "x y"})

    value, source = resolve_value_and_source(param, ctx, {})

    assert value == ["x", "y"]
    assert source is ParameterSource.DEFAULT_MAP


def test_parameter_default_is_the_last_resort():
    param = click.Option(["--port"], default=80)

    value, source = resolve_value_and_source(param, make_ctx(), {})

    assert value == 80
    assert source is ParameterSource.DEFAULT


def test_unset_value_reports_default_source():
    param = click.Option(["--port"])

    value, source = resolve_value_and_source(param, make_ctx(), {})

    assert value is UNSET
    assert source is ParameterSource.DEFAULT


def test_envvar_empty_string_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("APP_PORT", "")
    param = click.Option(["--port"], default=80, envvar="APP_PORT")

    value, source = resolve_value_and_source(param, make_ctx(), {})

    assert value == 80
    assert source is ParameterSource.DEFAULT


def test_flag_envvar_false_is_still_an_environment_value(monkeypatch):
    monkeypatch.setenv("APP_MODE", "no")
    param = click.Option(
        ["--mode"], is_flag=True, flag_value="fast", default="slow", envvar="APP_MODE"
    )

    value, source = resolve_value_and_source(param, make_ctx(), {})

    assert value is False
    assert source is ParameterSource.ENVIRONMENT


def test_resolution_does_not_prompt():
    # Prompting is layered on top by Option.consume_value; the resolution
    # layer itself never prompts and reports the underlying source.
    param = click.Option(["--user"], prompt=True, default="admin")

    value, source = resolve_value_and_source(param, make_ctx(), {})

    assert value == "admin"
    assert source is ParameterSource.DEFAULT


def test_consume_value_delegates_to_the_layer(monkeypatch):
    monkeypatch.setenv("APP_PORT", "2")
    param = click.Option(["--port"], default=80, envvar="APP_PORT")
    ctx = make_ctx()

    assert param.consume_value(ctx, {}) == ("2", ParameterSource.ENVIRONMENT)
    assert param.consume_value(ctx, {"port": 1}) == (
        1,
        ParameterSource.COMMANDLINE,
    )


@pytest.mark.parametrize(
    ("args", "env", "default_map", "expected_source"),
    [
        (["--port", "1"], {"APP_PORT": "2"}, {"port": 3}, ParameterSource.COMMANDLINE),
        ([], {"APP_PORT": "2"}, {"port": 3}, ParameterSource.ENVIRONMENT),
        ([], {}, {"port": 3}, ParameterSource.DEFAULT_MAP),
        ([], {}, {}, ParameterSource.DEFAULT),
    ],
)
def test_end_to_end_source_reported_on_context(
    runner, args, env, default_map, expected_source
):
    """The layer's decision is what Context.get_parameter_source reports."""
    seen = []

    @click.command()
    @click.option("--port", default=80, envvar="APP_PORT")
    @click.pass_context
    def cli(ctx, port):
        seen.append(ctx.get_parameter_source("port"))

    result = runner.invoke(cli, args, env=env, default_map=default_map)

    assert result.exit_code == 0
    assert seen == [expected_source]
