import argparse
import base64
import json
import sys

from io import BytesIO
from typing import Union

from .container import Container


def main():
    parser = argparse.ArgumentParser(
        description="IFF-based container/chunk parser utility."
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Input file path. If omitted, binary data is read from standard input.",
    )
    parser.add_argument(
        "--mode",
        choices=["container", "chunk"],
        default="container",
        help="Parsing mode: 'container' returns raw container data (with payloads omitted unless --show-payload is used), "
        "while 'chunk' returns parsed chunk values.",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help="List of chunk identifiers to ignore (improves performance if unwanted chunks are skipped).",
    )
    parser.add_argument(
        "--show-payload",
        action="store_true",
        help="In container mode, include the payload in the output.",
    )

    args = parser.parse_args()

    if args.source:
        source_input: Union[str, BytesIO] = args.source
    else:
        source_input = BytesIO(sys.stdin.buffer.read())

    if args.mode == "container":
        container = Container(source_input, ignore=args.ignore)
        _ = list(container.get_chunks())
        container_dict = container.container

        if not args.show_payload:
            for key, value in container.container.items():
                if "payload" in value and not args.show_payload:
                    new_val = dict(value)
                    del new_val["payload"]
                    container_dict[key] = new_val
                else:
                    container_dict[key] = value
        else:
            for key, value in container.container.items():
                new_val = dict(value)
                if "payload" in new_val:
                    if args.show_payload:
                        new_val["payload"] = base64.b64encode(
                            new_val["payload"]
                        ).decode("ascii")
                    else:
                        del new_val["payload"]
                container_dict[key] = new_val

        print(json.dumps(container_dict, indent=2))
    else:  #: mode == "chunk" | Handle when Chunk class is implemented
        ...


if __name__ == "__main__":
    main()
