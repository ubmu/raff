`raff` is a Python library and command-line utility for extensive reading and parsing of IFF-based container formats.

```py
#: Example usage:
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

TODO: Implement `Chunk` and add as many chunk parsers as possible.

```py
from raff import Chunk
#: Initialize the chunk parser.
chunk = Chunk(file)

#: Iterate over each chunk (excluding the master/header chunk):
for identifier, size, payload in chunk.get_chunks():
    #: Chunk().get_chunks() would wrap over the Container() version 
    #: and return a parsed payload dict rather than the raw bytes.
    ...
```
