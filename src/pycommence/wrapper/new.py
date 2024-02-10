from __future__ import annotations

from win32com.client import Dispatch
from win32com.universal import com_error

from .cmc_conversation import CommenceConversation
from .cmc_cursor import CmcCursor
from .cmc_enums import CursorType, OptionFlag
from ..entities import CmcError


class CmcAPI:
    connections = {}

    def __new__(cls, cmc_name: str = 'Commence.DB',
                cursor_names: list[str] | None = None):
        """
        Cache Commence db connection and cursor objects.
        """
        cursor_names = cursor_names or []
        if conn := cls.connections.get(cmc_name):
            return conn
        conn = CmcConnection(cmc_name, cursor_names)
        cls.connections[cmc_name] = conn
        return conn


class CmcConnection:
    def __init__(self, db_name='Commence.DB', cursor_names: list[str] | None = None):
        """Connect to a Commence Database."""
        cursor_names = cursor_names or []
        self.db_name = db_name
        self.cursors = {
            name: self.get_cursor(name)
            for name in cursor_names
        }

        try:
            self._cmc = Dispatch(db_name)
        except com_error as e:
            if e.hresult == -2147221005:
                raise CmcError(f'Db Name "{db_name}" does not exist - connection failed')
            raise e

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
            self, topic: str, application_name: str = 'Commence'
    ) -> CommenceConversation:
        """
        Create a conversation object, except probably just don't and go get a cursor instead.

        Args:
            application_name (str): DDE Application name. The only valid value is "Commence".
            topic (str): DDE Topic name, must be a valid Commence topic name.
                         Examples include "GetData", "ViewData", etc.

        Returns:
            CommenceConversation: A CommenceConversation object on success.

        Raises: ValueError if failure
        """
        conversation_obj = self._cmc.GetConversation(application_name, topic)
        if conversation_obj is None:
            raise ValueError(
                f'Could not create conversation object for {application_name}!{topic}'
            )
        return CommenceConversation(conversation_obj)

    def get_cursor(self,
                   name: str or None = None,
                   mode: CursorType = CursorType.CATEGORY,
                   flags: list[OptionFlag] or OptionFlag or None = None) -> CmcCursor:
        """
        Create a cursor object for accessing Commence data.
        CursorTypes CATEGORY and VIEW require name to be set.

        name (str|None): Name of an object in the database.
            For CMC_CURSOR_CATEGORY, name is the category name.
            For CMC_CURSOR_VIEW, name is the view name.

        flags (optional): Additional option flags. Logical OR of the following option flags:
            PILOT - Save Item agents defined for the Pilot subsystem will fire.
            INTERNET - Save Item agents defined for the Internet/intranet will fire.

        Returns:
        CommenceCursor: A CommenceCursor object on success.

        Raises: ValueError if no name given for name based searches

        """
        # todo can ther be multiple flags?
        if csr := self.cursors.get(name):
            return csr
        if flags:
            if isinstance(flags, OptionFlag):
                flags = [flags]
            for flag in flags:
                if flag not in [OptionFlag.PILOT, OptionFlag.INTERNET]:
                    raise ValueError(f'Invalid flag: {flag}')
            flags = ', '.join(str(f.value) for f in flags)

        else:
            flags = 0

        mode = mode.value
        if mode in [0, 1]:
            if name is None:
                raise ValueError(
                    f'Mode {mode} ("{CursorType(mode).name}") requires name param to be set')

        csr = CmcCursor(self._cmc.GetCursor(mode, name, flags))
        self.cursors[name] = csr
        return csr

        # todo fix errors on non-standard modes
