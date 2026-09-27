"""Centralized determination of where a parameter's value comes from.

This module is the single place that knows the precedence of the value
sources (command line, environment, default map, parameter default) and
maps a resolved value to its :class:`ParameterSource`.

It is kept separate from :class:`~click.core.Parameter` so that the
source-resolution policy can be unit tested on its own, without
involving the parser, prompting, or type casting. Parsing only splits
the command line into tokens; :meth:`~click.core.Parameter.consume_value`
only fetches the value and its source from here.
"""

from __future__ import annotations

import collections.abc as cabc
import enum
import typing as t

from ._utils import UNSET

if t.TYPE_CHECKING:
    from .core import Context
    from .core import Parameter


class ParameterSource(enum.IntEnum):
    """This is an :class:`~enum.IntEnum` that indicates the source of a
    parameter's value.

    Use :meth:`click.Context.get_parameter_source` to get the
    source for a parameter by name.

    Members are ordered from most explicit to least explicit source.
    This allows comparison to check if a value was explicitly provided:

    .. code-block:: python

        source = ctx.get_parameter_source("port")
        if source < click.ParameterSource.DEFAULT_MAP:
            ...  # value was explicitly set

    .. versionchanged:: 8.3.3
        Use :class:`~enum.IntEnum` and reorder members from most to
        least explicit. Supports comparison operators.

    .. versionchanged:: 8.0
        Use :class:`~enum.Enum` and drop the ``validate`` method.

    .. versionchanged:: 8.0
        Added the ``PROMPT`` value.
    """

    PROMPT = enum.auto()
    """Used a prompt to confirm a default or provide a value."""
    COMMANDLINE = enum.auto()
    """The value was provided by the command line args."""
    ENVIRONMENT = enum.auto()
    """The value was provided with an environment variable."""
    DEFAULT_MAP = enum.auto()
    """Used a default provided by :attr:`Context.default_map`."""
    DEFAULT = enum.auto()
    """Used the default specified by the parameter."""


def resolve_value_and_source(
    param: Parameter, ctx: Context, opts: cabc.Mapping[str, t.Any]
) -> tuple[t.Any, ParameterSource]:
    """Resolve a parameter's value and the source it came from.

    Sources are checked in order of precedence, most explicit first:

    #. the command line, i.e. the values produced by the parser,
    #. the environment, through :meth:`Parameter.value_from_envvar`,
    #. the context's :attr:`~click.Context.default_map`,
    #. the parameter's own default.

    If no source provides a value, the internal ``UNSET`` sentinel is
    returned, sourced as :attr:`ParameterSource.DEFAULT`.

    Prompting is deliberately *not* handled here. It is an interaction
    concern layered on top of this resolution by
    :meth:`click.core.Option.consume_value`.

    :meta private:
    """
    # The parser produced a value from user input on the command line.
    value = opts.get(param.name, UNSET)

    if value is not UNSET:
        return value, ParameterSource.COMMANDLINE

    envvar_value = param.value_from_envvar(ctx)

    if envvar_value is not None:
        return envvar_value, ParameterSource.ENVIRONMENT

    if ctx._default_map_has(param.name):
        default_map_value = ctx.lookup_default(param.name)

        # A string from default_map must be split for multi-value
        # parameters, matching value_from_envvar behavior.
        if isinstance(default_map_value, str) and param.nargs != 1:
            default_map_value = param.type.split_envvar_value(default_map_value)

        return default_map_value, ParameterSource.DEFAULT_MAP

    default_value = param.get_default(ctx)

    if default_value is not UNSET:
        return default_value, ParameterSource.DEFAULT

    return UNSET, ParameterSource.DEFAULT
