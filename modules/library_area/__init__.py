from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.Floor,
        library.Room,
        library.Shelf,
        library.Book,
        library.Exemplary,
        module='library_area', type_='model')

    Pool.register(
        module='library_area', type_='wizard')
