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
        wizard.MoveExemplariesSelectShelf,
        module='library_area', type_='model')

    Pool.register(
        wizard.MoveExemplaries,
        wizard.Borrow,
        module='library_area', type_='wizard')
