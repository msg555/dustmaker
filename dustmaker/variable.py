"""
Module defining the Dustforce variable representation
"""
import abc
import collections.abc
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple, Type


class VariableType(IntEnum):
    """Enumeration of Var type IDs."""

    #: Special code used in the internal format. Null variables cannot be created.
    NULL = 0
    BOOL = 1
    INT = 2
    UINT = 3
    FLOAT = 4
    #: Dustforce strings are actually byte arrays
    STRING = 5
    #: Vec2 is a (float, float) tuple
    VEC2 = 10
    #: Generic mapping/object type
    STRUCT = 14
    ARRAY = 15


class Variable(metaclass=abc.ABCMeta):
    """Variable base class. Variables are a mechanism Dustforce uses to make structure
    metadata easily available to the game script. Variables will raise an `AssertionError`
    if they are created with an invalid :attr:`value` attribute.

    Variables support the equality and hashing interface.

    Attributes:
        value: The internal value of this variable. Its type will depend on the
            actual variable type.
    """

    _TYPES: Dict[VariableType, Type["Variable"]] = {}
    _vtype = VariableType.NULL

    def __init__(self, value: Any) -> None:
        self.value = value
        self._assert_types()

    @classmethod
    def __init_subclass__(cls):
        """record type id to type class mapping"""
        if cls._vtype is not VariableType.NULL:
            Variable._TYPES[cls._vtype] = cls

    def __eq__(self, oth) -> bool:
        # pylint: disable=no-member
        if not isinstance(oth, Variable):
            return False
        return self._vtype == oth._vtype and self.value == oth.value

    def __hash__(self):
        # pylint: disable=no-member
        return hash((self._vtype, self.value))

    def assert_types(self) -> None:
        """Checks if the type of :attr:`value` matches our concrete variable type.

        Raises:
            ValueError: :attr:`value`'s type is invalid
        """
        try:
            self._assert_types()
        except AssertionError as e:
            raise ValueError("value does not match variable type") from e

    @abc.abstractmethod
    def _assert_types(self) -> None:
        """Assert that value types are correct, recursively"""

    def __repr__(self) -> str:
        # pylint: disable=no-member
        return "Variable(%s, %s)" % (repr(self._vtype), repr(self.value))


class VariableBool(Variable):
    """Represents a boolean variable of type :class:`bool`."""

    _vtype = VariableType.BOOL

    def __init__(self, value: bool = False) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is boolean"""
        assert isinstance(self.value, bool)


class VariableInt(Variable):
    """Represents a 32-bit signed int variable of type :class:`int`."""

    _vtype = VariableType.INT

    def __init__(self, value: int = 0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is int in range."""
        assert isinstance(self.value, int) and -(2 ** 31) <= self.value < 2 ** 31


class VariableUInt(Variable):
    """Represents a 32-bit unsigned int variable of type :class:`int`."""

    _vtype = VariableType.UINT

    def __init__(self, value: int = 0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is int in range."""
        assert isinstance(self.value, int) and 0 <= self.value < 2 ** 32


class VariableFloat(Variable):
    """Represents a floating point variable of type :class:`float`."""

    _vtype = VariableType.FLOAT

    def __init__(self, value: float = 0.0) -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is float."""
        assert isinstance(self.value, float)


class VariableString(Variable):
    """Represents a string variable of type :class:`bytes`."""

    _vtype = VariableType.STRING

    def __init__(self, value: bytes = b"") -> None:
        super().__init__(value)

    def _assert_types(self) -> None:
        """Ensure value is bytes."""
        assert isinstance(self.value, bytes)


class VariableVec2(Variable):
    """Represents a 2-dimensional vector of type `(float, float)`."""

    _vtype = VariableType.VEC2

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
    """Represents a struct (dictionary) mapping of type `dict[str, Variable]`."""

    _vtype = VariableType.STRUCT

    def __init__(self, value: Optional[Dict[str, Variable]] = None) -> None:
        super().__init__(dict(value or {}))

    def _assert_types(self) -> None:
        """Ensure value is dictionary of strs to Variables."""
        assert isinstance(self.value, dict)
        for key, val in self.value.items():
            assert isinstance(key, str) and isinstance(val, Variable)
            val._assert_types()


class VariableArray(Variable, collections.abc.MutableSequence):
    """Represents an array variable. Arrays are stored a bit differently
    because they must explicitly encode the type of their sub-elements
    (heterogenous arrays are not allowed).

    :class:`VariableArray` implements the :class:`collections.abc.MutableSequence`
    interface, automatically boxing and unboxing accessed elements.

    Arguments:

        element_type (type[Variable]): Variable type of all elements
        values (list[element_type]): Array of variables of type `element_type`

    Attributes:

        value (element_type, list[element_type]): A tuple containing the element
            type and the element list. Prefer using :attr:`element_type` and
            the :class:`MutableSequence` interface provided by VariableArray instead
            of accessing these elements through :attr:`value`.

    """

    _vtype = VariableType.ARRAY

    def __init__(
        self, element_type: Type[Variable], values: Optional[List[Variable]] = None
    ) -> None:
        super().__init__((element_type, list(values or [])))

    @property
    def element_type(self) -> Type[Variable]:
        """Element type of this array"""
        return self.value[0]

    def _box(self, val):
        """Helper method to box values in a Variable object. Basically just
        VariableArray is weird.
        """
        etype = self.value[0]
        if etype is VariableArray:
            return etype(*val)
        return etype(val)

    # Implement the MutableMapping abstract methods by forwarding to the
    # backing list. We unbox variables from their Variable packaging. This
    # is a little weird with arrays where the unboxed type is a (type, list)
    # tuple but works in principle.
    def __getitem__(self, key):
        return self.value[1][key].value

    def __setitem__(self, key, val):
        self.value[1][key] = self._box(val)

    def __delitem__(self, key):
        del self.value[1][key]

    def __len__(self):
        return len(self.value[1])

    # Method labeled as private since none of the other MutableSequence methods
    # are directly included in the docs.
    def insert(self, index, value):
        """Impelements the :class:`MutableSequence.insert` interface by inserting
        the boxed value into the backing variable list.

        :meta private:
        """
        self.value[1].insert(index, self._box(value))

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
