import pytest

import click
from click.parser import _OptionParser
from click.shell_completion import split_arg_string


@pytest.mark.parametrize(
    ("value", "expect"),
    [
        ("cli a b c", ["cli", "a", "b", "c"]),
        ("cli 'my file", ["cli", "my file"]),
        ("cli 'my file'", ["cli", "my file"]),
        ("cli my\\", ["cli", "my"]),
        ("cli my\\ file", ["cli", "my file"]),
    ],
)
def test_split_arg_string(value, expect):
    assert split_arg_string(value) == expect


def test_parser_default_prefixes():
    parser = _OptionParser()
    assert parser._opt_prefixes == {"-", "--"}


def test_parser_collects_prefixes():
    ctx = click.Context(click.Command("test"))
    parser = _OptionParser(ctx)
    click.Option("+p", is_flag=True).add_to_parser(parser, ctx)
    click.Option("!e", is_flag=True).add_to_parser(parser, ctx)
    assert parser._opt_prefixes == {"-", "--", "+", "!"}


def _make_parser(*options):
    ctx = click.Context(click.Command("test"))
    parser = _OptionParser(ctx)
    for option in options:
        option.add_to_parser(parser, ctx)
    return parser


@pytest.mark.parametrize(
    ("arg", "expect"),
    [
        ("--foo", ("--foo", None)),
        ("--foo=bar", ("--foo", "bar")),
        ("--foo=a=b", ("--foo", "a=b")),
    ],
)
def test_split_long_opt(arg, expect):
    parser = _make_parser()
    assert parser._split_long_opt(arg) == expect


def test_split_short_opts_flags():
    parser = _make_parser(
        click.Option(("-a",), is_flag=True),
        click.Option(("-b",), is_flag=True),
    )
    tokens = list(parser._split_short_opts("-ab"))
    assert [(ch, opt) for ch, opt, _, _ in tokens] == [("a", "-a"), ("b", "-b")]
    assert [option.dest for _, _, option, _ in tokens] == ["a", "b"]
    assert [attached for _, _, _, attached in tokens] == [None, None]


def test_split_short_opts_attached_value_ends_cluster():
    parser = _make_parser(
        click.Option(("-o",)),
        click.Option(("-f",), is_flag=True),
    )
    # The rest of the cluster becomes the value of the first option that
    # takes one, remaining characters are not split further.
    tokens = list(parser._split_short_opts("-ofile"))
    assert [(ch, opt, attached) for ch, opt, _, attached in tokens] == [
        ("o", "-o", "file")
    ]


def test_split_short_opts_unknown():
    parser = _make_parser()
    [(ch, opt, option, attached)] = list(parser._split_short_opts("-x"))
    assert (ch, opt, option, attached) == ("x", "-x", None, None)
