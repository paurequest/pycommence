from __future__ import annotations

import typing as _t

from loguru import logger
from win32com.client import Dispatch
from win32com.universal import com_error

from . import types_api
from ..wrapper import conversation, cursor, enums_cmc


class CmcConnection:
    """
    Handler for caching connections to one or more Commence instances

    """
    connections = {}

    def __new__(cls, commence_instance: str = 'Commence.DB') -> Cmc:
        if commence_instance in cls.connections:
            logger.info(f'Using cached connection to {commence_instance}')
        else:
            cls.connections[commence_instance] = super().__new__(cls)

        return cls.connections[commence_instance]

    def __init__(self, commence_instance='Commence.DB'):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db_name = commence_instance
            try:
                self._cmc = Dispatch(commence_instance)
            except com_error as e:
                if e.hresult == -2147221005:
                    raise types_api.CmcError(
                        f'Db Name "{commence_instance}" does not exist - connection failed'
                    )
                raise types_api.CmcError(
                    f'Error connecting to {commence_instance}. Is Commence Running?\n{e}'
                )


class Cmc(CmcConnection):
    """ Api for Commence database connection """

    @property
    def name(self) -> str:
        """(read-only) Name of the Commence database."""
        return self._cmc.Name

    @property
    def path(self) -> str:
        """(read-only) Full path of the Commence database."""
        return self._cmc.Path

    def __str__(self) -> str:
        return f'<CmcDB: "{self.name}">'

    def __repr__(self):
        return f"<CmcDB: {self.db_name}>"

    @property
    def registered_user(self) -> str:
        """(read-only) CR/LF delimited string with username, company name, and serial number."""
        return self._cmc.RegisteredUser

    @property
    def shared(self) -> bool:
        """(read-only) TRUE if the database is enrolled in a workgroup."""
        return self._cmc.Shared

    @property
    def version(self) -> str:
        """(read-only) Version number in x.y format."""
        return self._cmc.Version

    @property
    def version_ext(self) -> str:
        """(read-only) Version number in x.y.z.w format."""
        return self._cmc.VersionExt

    def get_conversation(
            self, topic: str, application_name: _t.Literal['Commence'] = 'Commence'
    ) -> conversation.CommenceConversation:
        """
        Create a conversation object, except probably just don't and go get a cursor instead.

        Args:
            topic (str): DDE Topic name, must be a valid Commence topic name.
            application_name (str): DDE Application name. The only valid value is "Commence".

        Returns:
            CommenceConversation: A CommenceConversation object on success.

        Raises:
            ValueError if failure.

        """

        conversation_obj = self._cmc.GetConversation(application_name, topic)
        if conversation_obj is None:
            raise ValueError(
                f'Could not create conversation object for {application_name}!{topic}'
            )
        return conversation.CommenceConversation(conversation_obj)

    def get_cursor(
            self,
            name: str or None = None,
            mode: enums_cmc.CursorType = enums_cmc.CursorType.CATEGORY,
            flags: list[enums_cmc.OptionFlag] or enums_cmc.OptionFlag or None = None
    ) -> cursor.CsrCmc:
        """
        Create a cursor object for accessing Commence data.
        CursorTypes CATEGORY and VIEW require name to be set.

        Args:
            name (str|None): Name of an object in the database.
                For CMC_CURSOR_CATEGORY, name is the category name.
                For CMC_CURSOR_VIEW, name is the view name.

            flags (optional): Additional option flags. Logical OR of the following option flags:
                PILOT - Save Item agents defined for the Pilot subsystem will fire.
                INTERNET - Save Item agents defined for the Internet/intranet will fire.

        Returns:
            CsrApi: A Csr object on success.

        Raises:
            ValueError if no name given for name based searches

        """
        # todo can ther be multiple flags?
        if flags:
            if isinstance(flags, enums_cmc.OptionFlag):
                flags = [flags]
            for flag in flags:
                if flag not in [enums_cmc.OptionFlag.PILOT, enums_cmc.OptionFlag.INTERNET]:
                    raise ValueError(f'Invalid flag: {flag}')
            flags = ', '.join(str(f.value) for f in flags)

        else:
            flags = 0

        mode = mode.value
        if mode in [0, 1]:
            if name is None:
                raise ValueError(
                    f'Mode {mode} ("{enums_cmc.CursorType(mode).name}") requires name param to be set'
                )
        try:
            csr = cursor.CsrCmc(self._cmc.GetCursor(mode, name, flags))
        except com_error as e:
            raise types_api.CmcError(f'Error creating cursor for {name}: {e}')
        return csr
        # todo non-standard modes
