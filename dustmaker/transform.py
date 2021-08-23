""" Module defining TxMatrix class used for affine transformations. """
import math
from typing import Iterable, Tuple, Union


class TxMatrix(tuple):
    """Immutable transformation matrix. This is a subclass of tuple that
    enforce itself to be a 3x3 affine transformation matrix.
    """

    IDENTITY: "TxMatrix"
    HFLIP: "TxMatrix"
    VFLIP: "TxMatrix"
    ROTATE: Tuple["TxMatrix", "TxMatrix", "TxMatrix", "TxMatrix"]

    def __new__(cls, matrix: Iterable[Iterable[float]]) -> "TxMatrix":
        mat = super().__new__(cls, (tuple(row) for row in matrix))  # type: ignore
        assert len(mat) == 3, "expected 3x3 matrix"
        assert all(len(row) == 3 for row in mat), "expected 3x3 matrix"
        assert all(
            isinstance(elem, (int, float)) for row in mat for elem in row
        ), "all elements must be ints or floats"
        assert mat[2] == (0, 0, 1), "last row must always be [0, 0, 1]"
        return mat

    def translate(self, x: float, y: float) -> "TxMatrix":
        """Add an additional translation to the transformation matrix.
        mat.translate(x, y) == TxMatrix.IDENTITY.translate(x, y) * mat
        """
        return TxMatrix(
            (
                (self[0][0], self[0][1], self[0][2] + x),
                (self[1][0], self[1][1], self[1][2] + y),
                (0, 0, 1),
            )
        )

    @property
    def angle(self) -> float:
        """Returns the amount a vertical line has been rotated clockwise
        in radians under this transformation.
        """
        return math.atan2(self[1][1], self[1][0]) - math.pi / 2

    @property
    def determinant(self) -> float:
        """Get the determinant of the transformation matrix"""
        return self[0][0] * self[1][1] - self[0][1] * self[1][0]

    @property
    def flipped(self) -> bool:
        """Returns True if the transformation matrix flips an axis. This is the
        same as the :attr:`determinant` being negative."""
        return self.determinant < 0

    @property
    def scale(self) -> float:
        """Returns the scaling of the transformation matrix. This is just the
        square root of the absolute value of the determinant which itself
        represents how much 2D areas expand in scale."""
        return math.sqrt(abs(self.determinant))

    def __mul__(self, rhs: Union[float, "TxMatrix"]) -> "TxMatrix":
        if isinstance(rhs, (int, float)):
            # Multiply by a scalar
            return TxMatrix(
                (
                    (self[0][0] * rhs, self[0][1] * rhs, self[0][2] * rhs),
                    (self[1][0] * rhs, self[1][1] * rhs, self[1][2] * rhs),
                    (0, 0, 1),
                )
            )

        # Matrix multiplication optimized for 2D affine matrixes.
        ml = self
        mr = rhs
        return TxMatrix(
            (
                (
                    ml[0][0] * mr[0][0] + ml[0][1] * mr[1][0],
                    ml[0][0] * mr[0][1] + ml[0][1] * mr[1][1],
                    ml[0][0] * mr[0][2] + ml[0][1] * mr[1][2] + ml[0][2],
                ),
                (
                    ml[1][0] * mr[0][0] + ml[1][1] * mr[1][0],
                    ml[1][0] * mr[0][1] + ml[1][1] * mr[1][1],
                    ml[1][0] * mr[0][2] + ml[1][1] * mr[1][2] + ml[0][2],
                ),
                (0, 0, 1),
            )
        )

    def __rmul__(self, lhs: Union[float]) -> "TxMatrix":
        return self * lhs

    def sample(self, x: float, y: float, *, with_offset=True) -> Tuple[float, float]:
        """Sample the transformed coordinates of (x, y)"""
        return (
            self[0][0] * x + self[0][1] * y + (self[0][2] if with_offset else 0),
            self[1][0] * x + self[1][1] * y + (self[1][2] if with_offset else 0),
        )


#: The identity matrix
TxMatrix.IDENTITY = TxMatrix(((1, 0, 0), (0, 1, 0), (0, 0, 1)))

#: Matrix representing a horizontal flip
TxMatrix.HFLIP = TxMatrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))

#: Matrix representing a vertical flip
TxMatrix.VFLIP = TxMatrix(((1, 0, 0), (0, -1, 0), (0, 0, 1)))

_CS = (1, 0, -1, 0)

#: ROTATE[i] gives the rotation matrix for rotating by 90-degrees
#: clockwise `i` times.
TxMatrix.ROTATE = tuple(  # type: ignore
    TxMatrix(((_CS[i], _CS[3 - i], 0), (_CS[(3 + i) & 0x3], _CS[i], 0), (0, 0, 1)))
    for i in range(4)
)
