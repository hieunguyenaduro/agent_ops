"""Tiện ích cho SSE.

Starlette có thể gọi `next()` của một generator đồng bộ trên nhiều thread
khác nhau trong threadpool. Điều đó bình thường với code thường, nhưng
OpenTelemetry (và Langfuse) lưu context theo thread/contextvar: span được
mở ở thread A mà đóng ở thread B sẽ sinh lỗi

    Failed to detach context ... was created in a different Context

và trace có thể mất quan hệ cha–con.

`preserve_context` giữ nguyên một context cho toàn bộ vòng đời generator,
dù nó được gọi từ thread nào. Đây là chi tiết hạ tầng nhỏ, nhưng thiếu nó
thì trace của endpoint streaming sẽ không đáng tin.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from typing import TypeVar

T = TypeVar("T")


def preserve_context(iterator: Iterator[T]) -> Iterator[T]:
    context = contextvars.copy_context()

    while True:
        try:
            yield context.run(next, iterator)
        except StopIteration:
            return
