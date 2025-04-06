import uuid

from typing import Any, Dict, Generator, List, Tuple, Union

from ._types import Byteorder
from .stream import Source, Stream, normalize_source

DEFAULT_ENCODING = "latin-1"
FALSE_MSIZE = "0xffffffff"
MASTER_BIG = ["FORM", "RIFX", "FIRR"]
MASTER_LITTLE = ["RIFF", "RF64", "BW64"]
NULL_IDENTIFIER = "\x00\x00\x00\x00"
SW64 = "riff"


RIFF_GUID = "66666972-912E-11CF-A5D6-28DB04C10000"
WAVE_GUID = "65766177-ACF3-11D3-8CD1-00C04F8EDB8A"


class Container:
    """
    IFF-based container format reader and parser.

    This class automatically determines and handles the endianness
    of the stream, and it extracts key metadata such as:

      - The byte order of the input stream.
      - The master (header) chunk, including file size and form-type identification.
      - The complete internal chunk structure, with each chunk's identifier, size,
        raw payload, and offset relative to the stream.

    """

    def __init__(self, source: Source, ignore: List[str] = []):
        """
        Initialize the container reader.

        Parameters
        ----------
        source : Source
            Input source to read from. Can be a file path, bytes object,
            or binary stream.

        ignore : List[str], optional
            List of chunk identifiers to skip during parsing.
            Useful for improving performance in certain situations.

        """
        try:
            self.stream: Stream = normalize_source(source)
        except ValueError:
            raise

        self.ignore = ignore

        self._byteorder: Byteorder = "little"
        self.chunk_identifiers: List[str] = []
        self.container: Dict[str, Any] = {}

    @property
    def byteorder(self) -> Byteorder:
        """The container byte-order."""
        return self._byteorder

    @property
    def master(self) -> Dict[str, Union[int, str]] | None:
        """The container header chunk."""
        return self.container.get("master")

    def chunk(self, identifier: str) -> Dict[str, Union[int, bytes]] | None:
        """Returns the size and payload of the specified chunk."""
        return self.container.get(identifier)

    def get_chunks(self) -> Generator[Tuple[str, int, bytes], None, None]:
        """Yields chunk identifiers, sizes, and raw payloads."""
        self.stream.reset()
        master = self.stream.read(4).decode(DEFAULT_ENCODING)

        if master == SW64:
            yield from self._sw64()
            return

        if master in MASTER_BIG:
            self._byteorder = "big"
        elif master not in MASTER_LITTLE:
            raise ValueError(f"Unknown master chunk identifier: {master}")

        msize_bytes = self.stream.read(4)
        msize = int.from_bytes(msize_bytes, byteorder=self._byteorder)

        #: FORM-TYPE / FILE-TYPE / ...
        ftype = self.stream.read(4).decode(DEFAULT_ENCODING)

        self.container["master"] = {
            "identifier": master,
            "size": msize,
            "type": ftype,
        }

        if hex(msize) == FALSE_MSIZE:
            #: -1. True size stored in [ds64] chunk.
            yield from self._rf64()
        else:
            yield from self._iff()

    def _iff(self) -> Generator[Tuple[str, int, bytes], None, None]:
        """IFF/RIFF/RIFX helper."""
        while True:
            offset = self.stream.tell()

            ident_bytes = self.stream.read(4)
            if len(ident_bytes) < 4:
                break

            identifier = ident_bytes.decode(DEFAULT_ENCODING)

            size_bytes = self.stream.read(4)
            if len(size_bytes) < 4:
                break

            size = int.from_bytes(size_bytes, byteorder=self._byteorder)

            #: Skip specified chunks
            if self.ignore and identifier in self.ignore:
                self.stream.seek(size, 1)
                continue

            payload = self.stream.read(size)
            self.chunk_identifiers.append(identifier)

            if identifier == "LIST":
                #: Determine the list-type and overwrite
                list_type = payload[:4].decode(DEFAULT_ENCODING).strip()
                size -= 12
                payload = payload[:4]

                self.container[identifier] = {
                    "offset": offset,
                    "size": size + 12,
                    "list_type": list_type,
                    "true_offset": offset + 8,
                    "true_size": size,
                    "payload": payload,
                }

                identifier = list_type
                self.chunk_identifiers.append(identifier)

            else:
                self.container[identifier] = {
                    "offset": offset,
                    "size": size,
                    "payload": payload,
                }

            yield (identifier, size, payload)

            #: Skip to next chunk, pad chunk size if odd
            if size % 2 != 0:
                size += 1

            self.stream.seek(size - len(payload), 1)

    def _read_int(self, nbytes: int = 4) -> int:
        return int.from_bytes(self.stream.read(nbytes), byteorder=self._byteorder)

    def _rf64(self) -> Generator[Tuple[str, int, bytes], None, None]:
        """RF64/BW64 helper."""

        #: The ['ds64'] chunk should come directly after the master chunk
        ds64_ident = self.stream.read(4).decode(DEFAULT_ENCODING)
        if ds64_ident != "ds64":
            raise ValueError(f"Expected ['ds64'] chunk, found: {ds64_ident}")

        self.chunk_identifiers.append(ds64_ident)

        self.container[ds64_ident] = {
            "chunk_size": self._read_int(),
            "riff_low_size": self._read_int(),
            "riff_high_size": self._read_int(),
            "data_low_size": self._read_int(),
            "data_high_size": self._read_int(),
            "sample_low_count": self._read_int(),
            "sample_high_count": self._read_int(),
            "table_entry_count": self._read_int(),
        }

        #: Update with correct size
        self.container["master"]["size"] = self.container[ds64_ident]["riff_low_size"]

        #: Ignore table_entry_count > 0 until a test file is found

        curr_loc = self.stream.tell()
        self.stream.seek(curr_loc + self.container["ds64"]["table_entry_count"] * 12)

        while True:
            offset = self.stream.tell()

            ident_bytes = self.stream.read(4)
            if len(ident_bytes) < 4:
                break

            identifier = ident_bytes.decode(DEFAULT_ENCODING)

            #: Get the correct chunk size from ['ds64']
            match identifier:
                case "data":
                    self.stream.read(4)
                    size = self.container["ds64"]["data_low_size"] + (
                        self.container["ds64"]["data_high_size"] << 32
                    )

                case "fact":
                    self.stream.read(4)
                    size = self.container["ds64"]["sample_low_count"] + (
                        self.container["ds64"]["sample_high_count"] << 32
                    )

                case _:
                    size_bytes = self.stream.read(4)
                    if len(size_bytes) < 4:
                        break

                    size = int.from_bytes(size_bytes, byteorder=self._byteorder)

            #: Skip specified chunks
            if self.ignore and identifier in self.ignore:
                self.stream.seek(size, 1)
                continue

            payload = self.stream.read(size)

            #: Some files seem to have all null bytes as the identifier
            if identifier != NULL_IDENTIFIER:
                self.chunk_identifiers.append(identifier)
                self.container[identifier] = {
                    "offset": offset,
                    "size": size,
                    "payload": payload,
                }
                yield (identifier, size, payload)

            #: Skip to next chunk, pad chunk size if odd
            if size % 2 != 0:
                size += 1

            self.stream.seek(size - len(payload), 1)

    def _sw64(self) -> Generator[Tuple[str, int, bytes], None, None]:
        """Sony Wave64 helper."""
        self.stream.reset()

        #: W64 chunk size MUST be an integral of 8 bytes.
        GUID_TO_FOURCC = {
            "66666972-912E-11CF-A5D6-28DB04C10000": "RIFF",
            "7473696C-912F-11CF-A5D6-28DB04C10000": "LIST",
            "65766177-ACF3-11D3-8CD1-00C04F8EDB8A": "WAVE",
            "20746D66-ACF3-11D3-8CD1-00C04F8EDB8A": "fmt ",
            "74636166-ACF3-11D3-8CD1-00C04F8EDB8A": "fact",
            "61746164-ACF3-11D3-8CD1-00C04F8EDB8A": "data",
            "6C76656C-ACF3-11D3-8CD1-00C04F8EDB8A": "levl",
            "6b6E756A-ACF3-11D3-8CD1-00C04f8EDB8A": "JUNK",
            "74786562-ACF3-11D3-8CD1-00C04F8EDB8A": "bext",
            "ABF76256-392D-11D2-86C7-00C04F8EDB8A": "MARKER",  # assume this is for cue
            "925F94BC-525A-11D2-86DC-00C04F8EDB8A": "SUMMARYLIST",  # idk
        }

        ident_guid = uuid.UUID(bytes_le=self.stream.read(16))

        if str(ident_guid) != RIFF_GUID:
            ValueError(f"Unknown RIFF GUID: {ident_guid}")

        #: Size here INCLUDES ['riff'] identifier, unlike RIFF/RF64.
        fsize_bytes = self.stream.read(8)
        fsize = int.from_bytes(fsize_bytes, byteorder="little")

        wave_guid = uuid.UUID(bytes_le=self.stream.read(16))

        if str(wave_guid) != WAVE_GUID:
            ValueError(f"Unknown WAVE GUID: {wave_guid}")

        self.container["master"] = {
            "identifier": "RIFF",
            "identifier_guid": str(ident_guid),
            "size": fsize,
            "type": "WAVE",
            "wave_guid": str(wave_guid),
        }

        while True:
            offset = self.stream.tell()

            ident_bytes = self.stream.read(16)
            if len(ident_bytes) < 16:
                break

            ident_guid = uuid.UUID(bytes_le=ident_bytes)

            size_bytes = self.stream.read(8)
            if len(size_bytes) < 8:
                break

            size = int.from_bytes(size_bytes, byteorder="little")

            chunk_identifier = GUID_TO_FOURCC.get(
                str(ident_guid).upper(), f"custom{len(self.container)}"
            )

            if (
                self.ignore
                and chunk_identifier in self.ignore
                or chunk_identifier.startswith("custom")
            ):
                self.stream.seek(offset + size)
                continue

            payload = self.stream.read(size)

            self.chunk_identifiers.append(chunk_identifier)
            self.container[chunk_identifier] = {
                "guid": str(ident_guid),
                "offset": offset,
                "size": size,
                "payload": payload,
            }

            yield (chunk_identifier, size, payload)

            #: 8-byte boundary alignment
            if size % 8 != 0:
                size += 1

            self.stream.seek(offset + size)
