from dataclasses import dataclass
from typing import Generic, TypeVar

from lessons_reporter_bot.callback_data import (
    ReportBuilderShowItemListCallbackData,
    ShowItemsListCallbackData,
)
from lessons_reporter_bot.models import FormattedPaginationItem

FIRST_PAGE = 1

PaginationItem = TypeVar('PaginationItem')


@dataclass
class PaginationResult(Generic[PaginationItem]):
    is_last_page: bool
    is_first_page: bool
    items: list[PaginationItem]


def paginate(
    items: list[PaginationItem], current_page: int, page_size: int
) -> PaginationResult[PaginationItem]:
    start = (current_page - 1) * page_size
    total_pages = (len(items) + page_size - 1) // page_size

    return PaginationResult(
        is_first_page=current_page == FIRST_PAGE,
        is_last_page=current_page == total_pages or len(items) == 0,
        items=items[start : start + page_size],
    )
