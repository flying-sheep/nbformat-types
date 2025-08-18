``nbformat`` types
==================

Re-export TypedDict versions of (currently) nbformat schemas
``v3_0``, ``v4_0``\ —\ ``v4_5`` (the latter also as ``current``).

Usage:

..  code-block:: python

    from typing import cast, TYPE_CHECKING
    import nbformat
    if TYPE_CHECKING:
        from nbformat_types import Document  # currently v4

    with open("Notebook.ipynb") as f:
        doc = cast(Document, nbformat.read(f, 4))
