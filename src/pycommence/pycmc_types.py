from __future__ import annotations

import typing as _t
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum, auto
from typing import Literal

from pydantic import BaseModel, Field

# from pycommence.api import csr_api

FilterConditionType = Literal['Equal To', 'Contains', 'After', 'Between', 'Before', 'Not Equal To', 'Not Contains']
FilterType = Literal['F', 'CTI', 'CTCF', 'CTCTI']
NotFlagType = Literal['Not', '']


class ConditionType(StrEnum):
    EQUAL = 'Equal To'
    CONTAIN = 'Contains'
    AFTER = 'After'
    BETWEEN = 'Is Between'
    BEFORE = 'Before'
    NOT_EQUAL = 'Not Equal To'
    NOT_CONTAIN = 'Not Contains'
    ON = 'On'


class NoneFoundHandler(StrEnum):
    ignore = auto()
    error = auto()


class RadioType(StrEnum):
    HYT = 'Hytera Digital'
    K_UHF = 'Kirisun UHF'
    K_VHF = 'Kirisun VHF'
    TES_289 = 'Tesunho SIM TH289'
    TES_288 = 'Tesunho SIM TH288'
    TES_389 = 'Tesunho SIM TH388'


class FilterArray(BaseModel):
    """Array of Cursor Filters."""

    filters: dict[int, CmcFilter] = Field(default_factory=dict)

    @classmethod
    def from_filters(cls, *filters: CmcFilter):
        return cls(filters={i: fil for i, fil in enumerate(list(filters), 1)})

    def __str__(self):
        return ', '.join([str(fil) for fil in self.filters.values()])


class CmcFilter(BaseModel):
    """Cursor Filter."""

    cmc_col: str
    f_type: FilterType = 'F'
    value: str = ''
    condition: ConditionType = 'Equal To'
    not_flag: NotFlagType = ''

    def __str__(self):
        return self.filter_str2(0)

    def filter_str2(self, slot: int) -> str:
        filter_str = (
            f'[ViewFilter({slot}, {self.f_type}, {self.not_flag}, {self.cmc_col}, {self.condition}{f', {self.value}' if self.value else ''})]'
        )
        return filter_str


@dataclass
class Connection:
    name: str
    from_table: str
    to_table: str


CmcDateFormat = '%Y%m%d'
CmcTimeFormat = '%H:%M'


def to_cmc_date(datecheck: date):
    return datecheck.strftime(CmcDateFormat)


def get_cmc_date(v: str) -> date:
    """Use CMC Cannonical flag"""
    if isinstance(v, datetime):
        return v.date()
    elif isinstance(v, date):
        return v
    elif isinstance(v, str):
        if v.isdigit():
            if len(v) == 8:
                return datetime.strptime(v, CmcDateFormat).date()
        if len(v) in [7, 10]:
            return datetime.fromisoformat(v).date()


def get_cmc_time(time_str: str):
    """Use CMC Cannonical flag"""
    return datetime.strptime(time_str, CmcTimeFormat).time()


