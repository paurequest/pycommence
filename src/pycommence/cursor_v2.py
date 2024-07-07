from __future__ import annotations

import contextlib
from collections.abc import Generator
from functools import cached_property
from typing import Self

from loguru import logger

from .exceptions import PyCommenceExistsError, raise_for_one
from .filters import ConditionType, FieldFilter, FilterArray
from .pycmc_types import Connection2, CursorType, MoreAvailable, Pagination, SeekBookmark
from .wrapper.cursor_wrapper import CursorWrapper


def raise_for_id_or_pk(id, pk):
    if not any([id, pk]):
        raise ValueError('Must provide id or pk')


class CursorAPI:
    def __init__(
            self,
            cursor_wrapper: CursorWrapper,
            mode: CursorType = CursorType.CATEGORY,
            csrname: str = '',
            filter_array: FilterArray | None = None,
    ):
        self.cursor_wrapper = cursor_wrapper
        self.mode = mode
        self.csrname = csrname
        self.filter_array = filter_array
        if self.filter_array:
            self.filter_by_array()

    # proxied from wrapper
    @cached_property
    def headers(self):
        """Column labels."""
        return self.cursor_wrapper.get_query_row_set(1).headers

    @property
    def category(self):
        """Commence Category name."""
        return self.cursor_wrapper.category

    @property
    def column_count(self):
        """Number of columns in the Cursor."""
        return self.cursor_wrapper.column_count

    @property
    def row_count(self):
        """Number of rows in the Cursor."""
        return self.cursor_wrapper.row_count

    @property
    def shared(self):
        """True if the database is enrolled in a workgroup."""
        return self.cursor_wrapper.shared

    # pk operations
    @cached_property
    def pk_label(self) -> str:
        """Column 0 label."""
        rs = self.cursor_wrapper.get_query_row_set(1)
        return rs.get_column_label(0)

    def pk_filter(self, pk, condition=ConditionType.EQUAL):
        field_filter = FieldFilter(column=self.pk_label, condition=condition, value=pk)
        return FilterArray.from_filters(field_filter)

    def pk_contains_filter(self, pk):
        return FilterArray.from_filters(FieldFilter(column=self.pk_label, condition=ConditionType.CONTAIN, value=pk))

    def pk_exists(self, pk: str) -> bool:
        """Check if primary key exists in the Cursor."""
        with self.temporary_filter(self.pk_filter(pk)):
            return self.row_count > 0

    def pk_to_id(self, pk: str) -> str:
        """Convert primary key to row ID."""
        with self.temporary_filter(self.pk_filter(pk)):
            rs = self.cursor_wrapper.get_query_row_set(2)
            raise_for_one(rs)
            return rs.get_row_id(0)

    def pk_to_row_ids(self, pk: str) -> list[str]:
        with self.temporary_filter(self.pk_filter(pk)):
            rs = self.cursor_wrapper.get_query_row_set()
            return [rs.get_row_id(i) for i in range(rs.row_count)]

    def row_id_to_pk(self, row_id: str) -> str:
        """Convert row ID to primary key."""
        rs = self.cursor_wrapper.get_query_row_set_by_id(row_id)
        return rs.get_value(0, 0)

    # CREATE
    def _create_row(self, create_pkg: dict[str, str]) -> None:
        pkg_pk = create_pkg.get(self.pk_label)
        if not pkg_pk:
            raise ValueError(f'Primary key {self.pk_label} not provided in create_pkg.')
        if self.pk_exists(pkg_pk):
            raise PyCommenceExistsError(f'Primary key {pkg_pk} already exists.')
        rs = self.cursor_wrapper.get_add_row_set(limit=1)
        rs.modify_row(0, create_pkg)
        rs.commit()

    # READ
    def _read_row(self, *, id: str | None = None, pk: str | None = None, with_category: bool = False) -> dict[str, str]:
        raise_for_id_or_pk(id, pk)
        id = id or self.pk_to_id(pk)
        rs = self.cursor_wrapper.get_query_row_set_by_id(id)
        raise_for_one(rs)
        row = rs.row_dicts_list()[0]
        if with_category:
            self.add_category_to_dict(row)
        return row

    def _read_rows(
            self,
            with_category: bool = False,
            pagination: Pagination = Pagination(),
            filter_array: FilterArray | None = None,
    ) -> Generator[
        dict[str, str] | MoreAvailable, None, None]:
        filter_manager = self.temporary_filter(filter_array) if filter_array else contextlib.nullcontext()
        if pagination.offset:
            self.cursor_wrapper.seek_row(SeekBookmark.CURRENT, pagination.offset)

        with filter_manager:
            rows_left = self.row_count - pagination.end
            rowset = self.cursor_wrapper.get_query_row_set(pagination.limit)

            for rownum, row in enumerate(rowset.rows(), start=pagination.offset + 1):
                if with_category:
                    self.add_category_to_dict(row)
                logger.debug(f'Yielding {self.category} #{rownum} "{row.get(self.pk_label)}"')
                yield row

            if rows_left > 0:
                logger.debug(f'{rows_left} More {self.category} rows available')
                yield MoreAvailable(n_more=rows_left)

    def _read_rows_filtered(
            self,
            filter_array: FilterArray,
            with_category: bool = False,
            pagination: Pagination | None = None,
    ) -> Generator[dict[str, str], None, None]:
        with self.temporary_filter(filter_array):
            yield from self._read_rows(pagination=pagination, with_category=with_category)

    # UPDATE
    def _update_row(self, update_pkg: dict, *, id: str | None = None, pk: str | None = None):
        raise_for_id_or_pk(id, pk)
        id = id or self.pk_to_id(pk)
        rs = self.cursor_wrapper.get_edit_row_set_by_id(id)
        rs.modify_row(0, update_pkg)
        assert rs.commit()

    # DELETE
    def _delete_row(self, id: str | None = None, pk: str | None = None) -> None:
        raise_for_id_or_pk(id, pk)
        id = id or self.pk_to_id(pk)
        rs = self.cursor_wrapper.get_delete_row_set_by_id(id)
        rs.delete_row(0)
        assert rs.commit()

    def add_category_to_dict(self, row):
        row.update({'category': self.category})

    # FILTER
    def filter_by_array(self) -> Self:
        """Enable the filter array."""
        filter_array = self.filter_array
        [self.cursor_wrapper.set_filter(filstr) for filstr in filter_array.filter_strs]
        if filter_array.sorts:
            self.cursor_wrapper.set_sort(filter_array.view_sort_text)
        if filter_array.logic:
            self.cursor_wrapper.set_filter_logic(filter_array.sort_logic_text)
        logger.info(f'Filtered {self.row_count} {self.category} pycommence rows from {filter_array}')
        return self

    @contextlib.contextmanager
    def temporary_filter(self, fil_array: FilterArray | None = None):
        """Temporarily filter by FilterArray object.

        Args:
            fil_array: FilterArray object

        """
        og_filter = self.filter_array.copy() if self.filter_array else None
        self.filter_array = fil_array
        try:
            self.filter_by_array()
            yield
        finally:
            self.filter_array = og_filter

    # @contextlib.contextmanager
    # def with_offset(self, offset: int):
    #     logger.warning(f'Offsetting {offset} rows')
    #     try:
    #         self.cursor_wrapper.seek_row(SeekBookmark.CURRENT, offset)
    #         yield
    #     finally:
    #         logger.warning('Resetting offset')
    #         self.cursor_wrapper.seek_row(SeekBookmark.BEGINNING, 0)
    #         logger.warning('Offset reset')

    def clear_filter(self, slot=1) -> None:
        self.cursor_wrapper.set_filter(f'[ViewFilter({slot},Clear)]')
        self.filter_array.filters.pop(slot, None)
        logger.debug(f'Cleared filter {slot}')

    def clear_all_filters(self) -> None:
        """Clear all filters."""
        [self.clear_filter(i) for i in range(1, 9)]
        self.filter_array = None
        logger.debug('Cleared all filters')

    def add_related_column(self, connection: Connection2) -> Self:
        """Add a related column to the cursor."""
        res = self.cursor_wrapper.set_related_column(
            col=self.column_count + 1,
            con_name=connection.name,
            connected_cat=connection.category,
            col_name=connection.column,
        )
        if not res:
            raise ValueError('Failed to add related column.')
        return self
