import datetime

from sql import Null
from sql.aggregate import Count

from trytond.model import ModelSQL, fields, ModelView, Unique
from trytond.model.fields import SQL_OPERATORS
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction

__all__ = [
    'Floor',
    'Room',
    'Shelf',
    'Book',
    'Exemplary'
    ]

BOOK_STATUS_UNDEFINED = 'undefined'
BOOK_STATUS_IN_RESERVE = 'in_reserve'
BOOK_STATUS_IN_SHELF = 'in_shelf'
BOOK_STATUS_BORROWED = 'borrowed'
BOOK_STATUS_IN_QUARANTINE = 'in_quarantine'

BOOK_STATUSES = [
    (BOOK_STATUS_UNDEFINED, 'UNDEFINED'),
    (BOOK_STATUS_IN_RESERVE, 'IN RESERVE'),
    (BOOK_STATUS_IN_SHELF, 'IN SHELF'),
    (BOOK_STATUS_BORROWED, 'BORROWED'),
    (BOOK_STATUS_IN_QUARANTINE, 'IN QUARANTINE')
    ]


class Floor(ModelSQL, ModelView):
    'Floor'
    __name__ = 'library.floor'

    rooms = fields.One2Many('library.room', 'floor', 'Rooms')
    name = fields.Char('Name', required=True, help='Name of the floor')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.name),
                'The floor must be unique!'),
            ]


class Room(ModelSQL, ModelView):
    'Room'
    __name__ = 'library.room'

    floor = fields.Many2One('library.floor', 'Floor', required=True,
        ondelete='CASCADE')
    shelves = fields.One2Many('library.shelf', 'room', 'Shelves')
    name = fields.Char('Name', required=True, help='Name of the room')
    number_of_exemplaries = fields.Function(
        fields.Integer('Number of exemplaries'),
        getter='getter_number_of_exemplaries')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.floor, t.name),
                'The room must be unique in its floor!'),
            ]

    @classmethod
    def getter_number_of_exemplaries(cls, rooms, name):
        result = {x.id: 0 for x in rooms}
        room = Pool().get('library.room').__table__()
        shelf = Pool().get('library.shelf').__table__()
        exemplary = Pool().get('library.book.exemplary').__table__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*room.join(shelf, condition=(room.id == shelf.room))
            .join(exemplary, condition=(shelf.id == exemplary.shelf))
            .select(room.id, Count(exemplary.id), group_by=[room.id]))
        for room_id, count in cursor.fetchall():
            result[room_id] = count
        return result


class Shelf(ModelSQL, ModelView):
    'Shelf'
    __name__ = 'library.shelf'

    room = fields.Many2One('library.room', 'Room', required=True,
        ondelete='CASCADE')
    exemplaries = fields.One2Many('library.book.exemplary', 'shelf',
        'Exemplaries')
    floor = fields.Function(
        fields.Many2One('library.floor', 'Floor'),
        getter='getter_floor')
    name = fields.Char('Name', required=True, help='Name of the shelf')
    number_of_exemplaries = fields.Function(
        fields.Integer('Number of exemplaries'),
        getter='getter_number_of_exemplaries')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.room, t.name),
                'The shelf must be unique in its room!'),
            ]

    @fields.depends('exemplaries')
    def on_change_with_number_of_exemplaries(self):
        return len(self.exemplaries or [])

    def getter_floor(self, name):
        return self.room.floor.id if self.room and self.room.floor else None

    @classmethod
    def getter_number_of_exemplaries(cls, shelves, name):
        result = {x.id: 0 for x in shelves}
        Exemplary = Pool().get('library.book.exemplary')
        exemplary = Exemplary.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary.select(exemplary.shelf, Count(exemplary.id),
                where=exemplary.shelf.in_([x.id for x in shelves]),
                group_by=[exemplary.shelf]))
        for shelf_id, count in cursor.fetchall():
            result[shelf_id] = count
        return result


class Book(metaclass=PoolMeta):
    __name__ = 'library.book'

    is_in_reserve = fields.Function(
        fields.Boolean('In reserve',
            help='If True, this book as at least one exemplary in reserve'),
        getter='getter_is_in_reserve', searcher='search_is_in_reserve')

    @classmethod
    def default_exemplaries(cls):
        return []  # needed to avoid default creation of one exemplary

    @classmethod
    def getter_is_in_reserve(cls, books, name):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        book = cls.__table__()
        result = {x.id: False for x in books}
        cursor = Transaction().connection.cursor()
        cursor.execute(*book
            .join(exemplary, condition=(exemplary.book == book.id))
            .join(checkout, 'LEFT OUTER',
                  condition=(exemplary.id == checkout.exemplary))
            .select(book.id, where=(
                    (checkout.return_date != Null) | (checkout.id == Null))
                    & (exemplary.shelf == Null)))
        for book_id, in cursor.fetchall():
            result[book_id] = True
        return result

    @classmethod
    def search_is_in_reserve(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        book = cls.__table__()
        query = (book.join(exemplary, condition=(exemplary.book == book.id))
                .join(checkout, 'LEFT OUTER',
                    condition=(exemplary.id == checkout.exemplary))
                .select(book.id, where=(
                        (checkout.return_date != Null)
                        | (checkout.id == Null)) & (exemplary.shelf == Null)))
        return [('id', 'in' if value else 'not in', query)]


class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    shelf = fields.Many2One('library.shelf', 'Shelf', ondelete='SET NULL',
        select=True)
    room = fields.Function(
        fields.Many2One('library.room', 'Room', select=True),
        getter='getter_room')
    floor = fields.Function(
        fields.Many2One('library.floor', 'Floor', select=True),
        getter='getter_floor')
    is_in_reserve = fields.Function(
        fields.Boolean('In reserve',
            help='If True, this exemplary is in reserve'),
        getter='getter_is_in_reserve', searcher='search_is_in_reserve')
    in_quarantine_date = fields.Date('In quarantine date',
        help='The date on which the exemplary entered in quarantine')
    out_quarantine_date = fields.Function(
        fields.Date('Out quarantine date',
            help='The date on which the book may be released from quarantine'),
        getter='on_change_with_out_quarantine_date',
        searcher='search_out_quarantine_date'
    )
    is_in_quarantine = fields.Function(
        fields.Boolean('In quarantine',
            help='If True, this exemplary is in quarantine'),
        getter='getter_is_in_quarantine', searcher='search_is_in_quarantine')

    status = fields.Function(
        fields.Selection(BOOK_STATUSES, 'Status', readonly=True, select=True),
        getter='on_change_with_status')

    @fields.depends('shelf', 'is_available', 'is_in_reserve')
    def on_change_with_status(self, name=None):
        status = BOOK_STATUS_UNDEFINED
        if self.is_in_quarantine:
            status = BOOK_STATUS_IN_QUARANTINE
        elif self.is_available is True:
            if self.is_in_reserve:
                status = BOOK_STATUS_IN_RESERVE
            else:
                status = BOOK_STATUS_IN_SHELF
        elif self.is_available is False:
            status = BOOK_STATUS_BORROWED
        return status

    @fields.depends('in_quarantine_date')
    def on_change_with_out_quarantine_date(self, name=None):
        if self.in_quarantine_date is None:
            return None
        return self.in_quarantine_date + datetime.timedelta(days=7)

    def getter_room(self, name):
        return self.shelf.room.id if self.shelf and self.shelf.room else None

    def getter_floor(self, name):
        return self.room.floor.id if self.room and self.room.floor else None

    @classmethod
    def getter_is_in_reserve(cls, exemplaries, name):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        result = {x.id: False for x in exemplaries}
        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary
            .join(checkout, 'LEFT OUTER',
                condition=(exemplary.id == checkout.exemplary))
            .select(exemplary.id, where=(
                    (checkout.return_date != Null) | (checkout.id == Null))
                    & (exemplary.shelf == Null)))
        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True
        return result

    @classmethod
    def getter_is_in_quarantine(cls, exemplaries, name):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        result = {x.id: False for x in exemplaries}
        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary
            .join(checkout, 'LEFT OUTER',
                condition=(exemplary.id == checkout.exemplary))
            .select(exemplary.id,
                where=((checkout.return_date != Null) | (checkout.id == Null))
                    & (exemplary.in_quarantine_date != Null)))
        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True
        return result

    @classmethod
    def search_is_in_reserve(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        query = (exemplary
            .join(checkout, 'LEFT OUTER',
                condition=(exemplary.id == checkout.exemplary))
            .select(exemplary.id, where=(
                    (checkout.return_date != Null) | (checkout.id == Null))
                    & (exemplary.shelf == Null)))
        return [('id', 'in' if value else 'not in', query)]

    @classmethod
    def search_is_in_quarantine(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        query = (exemplary
            .join(checkout, 'LEFT OUTER',
                condition=(exemplary.id == checkout.exemplary))
            .select(exemplary.id, where=(
                    (checkout.return_date != Null) | (checkout.id == Null))
                    & (exemplary.in_quarantine_date != Null)))
        return [('id', 'in' if value else 'not in', query)]

    @classmethod
    def search_out_quarantine_date(cls, name, clause):
        exemplary = cls.__table__()
        _, operator, value = clause
        if isinstance(value, datetime.date):
            value = value + datetime.timedelta(days=-7)
        if isinstance(value, (list, tuple)):
            value = [(x + datetime.timedelta(days=-7) if x else x)
                     for x in value]
        Operator = SQL_OPERATORS[operator]
        query = exemplary.select(exemplary.id,
            where=Operator(exemplary.in_quarantine_date, value))
        return [('id', 'in', query)]
