import typing as _t

import pydantic as _p

from pycommence.api import CmcError, csr_api_handled
from pycommence.api.csr_api import EmptyKind


class CmcHandler(_p.BaseModel):
    """
    handle cursors to retrieve data with different filter configurations
    """
    csr: csr_api_handled.Csr

    model_config = _p.ConfigDict(
        arbitrary_types_allowed=True,
    )

    def records(self, count: int or None = None) -> list[dict[str, str]]:
        row_set = self.csr.get_query_rowset(count)
        records = row_set.get_row_dicts()
        return records

    def one_record(self, pk_val: str) -> dict[str, str]:
        with self.csr.temporary_filter_pk(pk_val):
            return self.records()[0]

    def records_by_field(
            self, field_name: str,
            value: str,
            max_rtn=None,
            empty: _t.Literal['ignore', 'raise'] = 'raise'
    ) -> list[dict[str, str]]:
        """
        Get records from the cursor by field name and value.

        Args:
            field_name: Name of the field to query.
            value: Value to filter by.
            max_rtn: Maximum number of records to return. If more than this, raise CmcError.
            empty: Action to take if no records are found. Options are 'ignore', 'raise'.

        Returns:
            A list of dictionaries of field names and values for the record.

        Raises:
            CmcError: If the record is not found or if more than max_rtn records are found.

        """
        with self.csr.temporary_filter_fields(field_name, 'Equal To', value, empty=empty):
            records = self.records()
            if not records and empty == 'raise':
                raise CmcError(f'No record found for {field_name} {value}')
            if max_rtn and len(records) > max_rtn:
                raise CmcError(f'Expected max {max_rtn} records, got {len(records)}')
            return records

    def edit_record(
            self,
            pk_val: str,
            package: dict,
    ) -> bool:
        """Modify a record in the cursor and commit.

        Args:
            pk_val (str): The value for the primary key field.
            package (dict): A dictionary of field names and values to modify.

        Returns:
            bool: True on success

            """
        with self.csr.temporary_filter_pk(pk_val):
            row_set = self.csr.get_edit_rowset()
            row_set.modify_row_dict(0, package)
            return row_set.commit()

    def delete_record(self, pk_val: str, empty: EmptyKind = 'raise'):
        """Delete a record from the cursor and commit.

        Args:
            pk_val (str): The value for the primary key field.
            empty (str): Action to take if the record is not found. Options are 'ignore', 'raise'.

        Returns:
            bool: True on success
        """
        with self.csr.temporary_filter_pk(pk_val, empty=empty):  # noqa: PyArgumentList
            if self.csr.row_count == 0 and empty == 'ignore':
                return
            row_set = self.csr.get_delete_rowset()
            row_set.delete_row(0)
            res = row_set.commit()
            return res

    def add_record(
            self,
            pk_val: str,
            package: dict,
            existing: _t.Literal['replace', 'update', 'raise'] = 'raise'
    ) -> bool:
        """
        Add and commit a record to the cursor.

        Args:
            pk_val: The value for the primary key field.
            package: A dictionary of field names and values to add to the record.
            existing: Action to take if the record already exists. Options are 'replace', 'update', 'raise'.

        Returns:
            bool: True on success
            """
        with self.csr.temporary_filter_pk(pk_val, empty='ignore'):  # noqa: PyArgumentList
            if not self.csr.row_count:
                row_set = self.csr.get_named_addset(pk_val)
            else:
                if existing == 'raise':
                    raise CmcError('Record already exists')
                elif existing == 'update':
                    row_set = self.csr.get_edit_rowset()
                elif existing == 'replace':
                    self.delete_record(pk_val)
                    row_set = self.csr.get_named_addset(pk_val)

            row_set.modify_row_dict(0, package)
            res = row_set.commit()
            return res
