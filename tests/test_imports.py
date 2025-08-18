from __future__ import annotations


def test_imports() -> None:
    from nbformat_types.versions import (  # noqa: PLC0415
        current,
        v3,
        v3_0,
        v4,
        v4_0,
        v4_1,
        v4_2,
        v4_3,
        v4_4,
        v4_5,
    )

    assert v3 is v3_0
    assert v4 is v4_5 is current

    del v4_0, v4_1, v4_2, v4_3, v4_4
