"""Reference systems-under-test for the benchmark.

- naive: always answers with the top lexical match; never abstains. The strawman that
  shows the over-responsiveness failure the benchmark is built to catch.
- grounded: the cite-or-refuse method (BM25 + undocumented-term gate + IDF relevance floor),
  ported to spans. Abstains when the corpus doesn't support an answer.
"""

from .grounded import build_grounded
from .naive import build_naive

__all__ = ["build_grounded", "build_naive"]
