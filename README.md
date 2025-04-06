`raff` is a Python library and command-line utility for extensive reading and parsing of IFF-based container formats.

### Usage

Install the package.

```$ pip install raff```

To start with the CLI, run the following command to see the help message:

Currently, only `--mode container` is supported. 

```
$ raff --help
usage: raff [-h] [--mode {container,chunk}] [--ignore [IGNORE ...]] [--show-payload] [source]

IFF-based container/chunk parser utility.

positional arguments:
  source                Input file path. If omitted, binary data is read from standard input.

options:
  -h, --help            show this help message and exit
  --mode {container,chunk}
                        Parsing mode: 'container' returns raw container data (with payloads
                        omitted unless --show-payload is used), while 'chunk' returns parsed
                        chunk values.
  --ignore [IGNORE ...]
                        List of chunk identifiers to ignore (improves performance if unwanted
                        chunks are skipped).
  --show-payload        In container mode, include the payload in the output.
```

Using the CLI with a file and the `--ignore` and `--show-payload` options:

```
$ raff some_file.catalog --mode container --ignore STRS --show-payload 
{
  "master": {
    "identifier": "FORM",
    "size": 6598,
    "type": "CTLG"
  },
  "FVER": {
    "offset": 12,
    "size": 38,
    "payload": "JFZFUjogVElGRlZpZXcuY2F0YWxvZyAzLjEzICgxMi4xLjk2KQA="
  },
  "LANG": {
    "offset": 58,
    "size": 8,
    "payload": "ZXNwYfFvbAA="
  },
  "CSET": {
    "offset": 74,
    "size": 32,
    "payload": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
  }
}
```

Using the CLI with piped input:

```
$ cat some_file.catalog | raff --mode container 
{
  "master": {
    "identifier": "FORM",
    "size": 6598,
    "type": "CTLG"
  },
  "FVER": {
    "offset": 12,
    "size": 38
  },
  "LANG": {
    "offset": 58,
    "size": 8
  },
  "CSET": {
    "offset": 74,
    "size": 32
  },
  "STRS": {
    "offset": 114,
    "size": 6484
  }
}
```

You can also use `raff` as a library. Here's an example:

```py
from raff import Container

#: File-like objects, raw bytes, or file paths are all valid inputs.
file = "some_file.iff"

#: Initialize the container reader.
container = Container(file)

#: You can also ignore certain chunks from being read. 
#: This can be useful for improving performance in certain situations.
container = Container(file, ignore=["JUNK", "FLLR", "PAD ", "fake", "DGDA"])

#: Iterate over each chunk (excluding the master/header chunk):
for identifier, size, payload in container.get_chunks():
    #: Process each chunk (identifier, size, payload)
    ...

#: Access the master (header) chunk:
print(container.master)
#: Display the master chunk's size.
#: (For standard RIFF files, add 8 to this value to obtain the full file size,
#:  unless a .w64 file was provided.)
print(container.master["size"])
#: Display the form type (e.g., file type such as 'WAVE').
print(container.master["type"])
#: List all chunk identifiers encountered.
print(container.chunk_identifiers)

#: NOTE: Some chunk payloads may be very large. When printing, consider omitting the payload.

#: Retrieve data for a specific chunk (e.g., the 'fmt ' chunk).
print(container.chunk("fmt "))

#: Display the full container dictionary, which includes all chunks (excluding ignored ones)
#: along with the master header.
print(container.container)
```

And once the `Chunk` parser is implemented, you can use it like so:

```py
from raff import Chunk

#: Initialize the chunk parser.
chunk = Chunk(file)

#: Iterate over each chunk, with payloads parsed rather than raw.
for identifier, size, parsed_payload in chunk.get_chunks():
    #: Process the parsed chunk data...
    ...

```
