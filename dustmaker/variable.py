"""
Module defining the Dustforce variable representation
"""
import abc
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple, Type


class VariableType(IntEnum):
    """Enumeration of Var type IDs."""

    NULL = 0
    BOOL = 1
    INT = 2
    UINT = 3
    FLOAT = 4
    STRING = 5
    VEC2 = 10
    STRUCT = 14
    ARRAY = 15


class Variable(metaclass=abc.ABCMeta):
    """Represents a variable attached to a Dustforce object."""

    TYPES: Dict[VariableType, Type["Variable"]] = {}
    vtype = VariableType.NULL

    def __init__(self, value: Any) -> None:
        self.value = value
        self._assert_types()

    @classmethod
    def __init_subclass__(cls):
        """record type id to type class mapping"""
        if cls.vtype is not VariableType.NULL:
            Variable.TYPES[cls.vtype] = cls

    def __eq__(self, oth) -> bool:
        # pylint: disable=no-member
        if not isinstance(oth, Variable):
            return False
        return self.vtype == oth.vtype and self.value == oth.value

    def __hash__(self):
        # pylint: disable=no-member
        return hash((self.vtype, self.value))

    def assert_types(self) -> None:
        """Raises a ValueError if the value does not correctly match the
        type of the Variable."""
        try:
            self._assert_types()
        except AssertionError as e:
            raise ValueError("value does not match variable type") from e

    @abc.abstractmethod
    def _assert_types(self) -> None:
        """Assert that value types are correct, recursively"""

    def __repr__(self) -> str:
        # pylint: disable=no-member
        return "Variable(%s, %s)" % (repr(self.vtype), repr(self.value))


class VariableBool(Variable):
    """Bool variable"""

    vtype = VariableType.BOOL

    def __init__(self, value: bool = False) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is boolean"""
        assert isinstance(self.value, bool)


class VariableInt(Variable):
    """32-bit signed int variable"""

    vtype = VariableType.INT

    def __init__(self, value: int = 0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is int in range."""
        assert isinstance(self.value, int) and -(2 ** 31) <= self.value < 2 ** 31


class VariableUInt(Variable):
    """32-bit unsigned int variable"""

    vtype = VariableType.UINT

    def __init__(self, value: int = 0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is int in range."""
        assert isinstance(self.value, int) and 0 <= self.value < 2 ** 32


class VariableFloat(Variable):
    """floating point variable"""

    vtype = VariableType.FLOAT

    def __init__(self, value: float = 0.0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is float."""
        assert isinstance(self.value, float)


class VariableString(Variable):
    """string (really, bytes) variable"""

    vtype = VariableType.STRING

    def __init__(self, value: bytes = b"") -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is bytes."""
        assert isinstance(self.value, bytes)


class VariableVec2(Variable):
    """vec2 (floating point pair) variable"""

    vtype = VariableType.VEC2

    def __init__(self, value: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure tuple of two floats."""
        assert (
            isinstance(self.value, tuple)
            and len(self.value) == 2
            and isinstance(self.value[0], float)
            and isinstance(self.value[1], float)
        )


class VariableStruct(Variable):
    """struct variable"""

    vtype = VariableType.STRUCT

    def __init__(self, value: Optional[Dict[str, Variable]] = None) -> None:
        super().__init__(dict(value or {}))

    def _assert_types(self) -> None:
        """Ensure value is dictionary of strs to Variables."""
        assert isinstance(self.value, dict)
        for key, val in self.value.items():
            assert isinstance(key, str) and isinstance(val, Variable)
            val._assert_types()


class VariableArray(Variable):
    """array variable"""

    vtype = VariableType.ARRAY

    def __init__(
        self, element_type: Type[Variable], values: Optional[List[Variable]] = None
    ) -> None:
        super().__init__((element_type, list(values or [])))

    def element_type(self) -> Type[Variable]:
        """Returns the element type of this array."""
        return self.value[0]

    def clear(self):
        """Forwards to clear on the underlying array"""
        self.value[1].clear()

    # Forwards a bunch of methods of the underlying list.
    def __len__(self):
        return len(self.value[1])

    # We unbox variables from their Variable packaging. This doesn't work
    # correctly for recursive types like element arrays or structs and you
    # should not use these convenience methods on those types.
    def append(self, x):
        """Wrapper around list.append of the value"""
        self.value[1].append(self.value[0](x))

    def pop(self, i=-1):
        """Wrapper around list.pop of the value"""
        return self.value[1].pop(i).value

    def __iter__(self):
        return (x.value for x in self.value[1].__iter__())

    def __getitem__(self, key):
        return self.value[1].__getitem__(key).value

    def __setitem__(self, key, val):
        return self.value[1].__setitem__(self.value[0](val))

    def __contains__(self, item):
        return self.value[1].__contains__(item)

    def __reversed__(self):
        return self.value[1].__reversed__()

    def _assert_types(self) -> None:
        """Ensure value is tuple of type and list of variables."""
        assert (
            isinstance(self.value, tuple)
            and len(self.value) == 2
            and isinstance(self.value[0], type)
            and issubclass(self.value[0], Variable)
            and isinstance(self.value[1], list)
        )
        for elem in self.value[1]:
            assert isinstance(elem, self.value[0])
            elem._assert_types()
