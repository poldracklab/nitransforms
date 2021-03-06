# emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NiBabel package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common interface for transforms."""
from collections.abc import Iterable

from .base import (
    TransformBase,
    TransformError,
)
from .linear import Affine
from .nonlinear import DisplacementsFieldTransform


class TransformChain(TransformBase):
    """Implements the concatenation of transforms."""

    __slots__ = ("_transforms",)

    def __init__(self, transforms=None):
        """Initialize a chain of transforms."""
        super().__init__()
        self._transforms = None

        if transforms is not None:
            self.transforms = transforms

    def __add__(self, b):
        """
        Compose this and other transforms.

        Example
        -------
        >>> T1 = TransformBase()
        >>> added = T1 + TransformBase() + TransformBase()
        >>> isinstance(added, TransformChain)
        True

        >>> len(added.transforms)
        3

        """
        self.append(b)
        return self

    def __getitem__(self, i):
        """
        Enable indexed access of transform chains.

        Example
        -------
        >>> T1 = TransformBase()
        >>> chain = T1 + TransformBase()
        >>> chain[0] is T1
        True

        """
        return self.transforms[i]

    def __len__(self):
        """Enable using len()."""
        return len(self.transforms)

    @property
    def transforms(self):
        """Get the internal list of transforms."""
        return self._transforms

    @transforms.setter
    def transforms(self, value):
        self._transforms = _as_chain(value)
        if self.transforms[-1].reference:
            self.reference = self.transforms[-1].reference

    def append(self, x):
        """
        Concatenate one element to the chain.

        Example
        -------
        >>> chain = TransformChain(transforms=TransformBase())
        >>> chain.append((TransformBase(), TransformBase()))
        >>> len(chain)
        3

        """
        self.transforms += _as_chain(x)

    def insert(self, i, x):
        """
        Insert an item at a given position.

        Example
        -------
        >>> chain = TransformChain(transforms=[TransformBase(), TransformBase()])
        >>> chain.insert(1, TransformBase())
        >>> len(chain)
        3

        >>> chain.insert(1, TransformChain(chain))
        >>> len(chain)
        6

        """
        self.transforms = self.transforms[:i] + _as_chain(x) + self.transforms[i:]

    def map(self, x, inverse=False):
        """
        Apply a succession of transforms, e.g., :math:`y = f_3(f_2(f_1(f_0(x))))`.

        Example
        -------
        >>> chain = TransformChain(transforms=[TransformBase(), TransformBase()])
        >>> chain([(0., 0., 0.), (1., 1., 1.), (-1., -1., -1.)])
        [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (-1.0, -1.0, -1.0)]

        >>> chain([(0., 0., 0.), (1., 1., 1.), (-1., -1., -1.)], inverse=True)
        [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (-1.0, -1.0, -1.0)]

        >>> TransformChain()((0., 0., 0.))  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        TransformError:

        """
        if not self.transforms:
            raise TransformError("Cannot apply an empty transforms chain.")

        transforms = self.transforms
        if not inverse:
            transforms = self.transforms[::-1]

        for xfm in transforms:
            x = xfm(x, inverse=inverse)

        return x

    def asaffine(self):
        """Combine a succession of linear transforms into one."""
        retval = self.transforms[-1]
        for xfm in self.transforms[:-1][::-1]:
            retval @= xfm
        return retval

    @classmethod
    def from_filename(cls, filename, fmt="X5", reference=None, moving=None):
        """Load a transform file."""
        from .io import itk

        retval = []
        if str(filename).endswith(".h5"):
            reference = None
            xforms = itk.ITKCompositeH5.from_filename(filename)
            for xfmobj in xforms:
                if isinstance(xfmobj, itk.ITKLinearTransform):
                    retval.append(Affine(xfmobj.to_ras(), reference=reference))
                else:
                    retval.append(DisplacementsFieldTransform(xfmobj))

            return TransformChain(retval)

        raise NotImplementedError


def _as_chain(x):
    """Convert a value into a transform chain."""
    if isinstance(x, TransformChain):
        return x.transforms
    if isinstance(x, Iterable):
        return list(x)
    return [x]


load = TransformChain.from_filename
