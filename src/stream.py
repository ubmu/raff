from io import BufferedReader, BytesIO
from pathlib import Path
from typing import Protocol, Union


class ReadableStream(Protocol):
    def read(self, size: int = -1) -> bytes:
        ...

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        ...

    def tell(self) -> int:
        ...

    def reset(self) -> None:
        ...


class FileSource(ReadableStream):
    def __init__(self, fp: Union[Path, str]):
        self._stream = open(fp, "rb")

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def reset(self) -> None:
        self._stream.seek(0)

    def close(self) -> None:
        self._stream.close()


class BinarySource(ReadableStream):
    def __init__(self, stream: Union[BytesIO, BufferedReader]):
        self._stream = stream

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def reset(self) -> None:
        self._stream.seek(0)


class ByteSource(ReadableStream):
    def __init__(self, data: bytes):
        self._stream = BytesIO(data)  # wrap

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def reset(self) -> None:
        self._stream.seek(0)


Source = Union[bytes, BytesIO, BufferedReader, Path, str]
Stream = Union[BinarySource, ByteSource, FileSource]


def normalize_source(source: Source) -> Stream:
    """Normalize source input into a stream."""

    if isinstance(source, (BufferedReader, BytesIO)):
        return BinarySource(source)

    elif isinstance(source, bytes):
        return ByteSource(source)

    elif isinstance(source, (str, Path)) and Path(source).is_file():
        return FileSource(source)

    else:
        raise ValueError(
            f"Invalid source type: {type(source)}. Expected file path, binary source, or bytes."
        )
