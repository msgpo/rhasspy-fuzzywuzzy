"""Rhasspy intent recognition with rapidfuzz"""
import logging
import time
import typing

import networkx as nx
import rapidfuzz.process as fuzzy_process
import rapidfuzz.utils as fuzz_utils
import rhasspynlu
from rhasspynlu.intent import Recognition

from .const import ExamplesType
from .train import train

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


def recognize(
    input_text: str,
    intent_graph: nx.DiGraph,
    examples: ExamplesType,
    intent_filter: typing.Optional[typing.Callable[[str], bool]] = None,
    extra_converters: typing.Optional[
        typing.Dict[str, typing.Callable[..., typing.Any]]
    ] = None,
) -> typing.List[Recognition]:
    """Find the closest matching intent(s)."""
    start_time = time.perf_counter()
    intent_filter = intent_filter or (lambda i: True)
    choices: typing.Dict[str, typing.List[int]] = {
        text: path
        for intent_name, paths in examples.items()
        if intent_filter(intent_name)
        for text, path in paths.items()
    }

    # Find closest match
    # pylint: disable=unpacking-non-sequence
    best_text, best_score = fuzzy_process.extractOne(
        fuzz_utils.default_process(input_text), choices.keys(), processor=None
    )
    _LOGGER.debug("input=%s, match=%s, score=%s", input_text, best_text, best_score)
    best_path = choices[best_text]

    end_time = time.perf_counter()
    _, recognition = rhasspynlu.fsticuffs.path_to_recognition(
        best_path, intent_graph, extra_converters=extra_converters
    )

    assert recognition and recognition.intent, "Failed to find a match"
    recognition.intent.confidence = best_score / 100.0
    recognition.recognize_seconds = end_time - start_time
    recognition.raw_text = input_text
    recognition.raw_tokens = input_text.split()

    return [recognition]
