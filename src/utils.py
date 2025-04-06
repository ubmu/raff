from ._types import Byteorder


def utils_symbol(byteorder: Byteorder) -> str:
    """Returns the corresponding byteorder symbol for stuct."""
    match byteorder:
        case "big":
            return ">"
        case "little":
            return "<"
        case _:
            raise ValueError("Invalid byteorder. Use 'big' or 'little'.")
