from datetime import datetime
import uuid

class LogEntry:
    """Represents a single transaction or change record in the system."""
    def __init__(self, action, item_title, person_name, log_id=None, timestamp=None):
        self.log_id = log_id if log_id else str(uuid.uuid4())[:8]
        self.timestamp = timestamp if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.action = action
        self.item_title = item_title
        self.person_name = person_name

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "item_title": self.item_title,
            "person_name": self.person_name
        }

    @staticmethod
    def from_dict(data):
        return LogEntry(
            data['action'],
            data['item_title'],
            data['person_name'],
            data.get('log_id'),
            data.get('timestamp')
        )

class Author:
    """Represents an author of a book."""
    def __init__(self, name, nationality="Unknown"):
        self.name = name
        self.nationality = nationality

    def to_dict(self):
        return {"name": self.name, "nationality": self.nationality}

    @staticmethod
    def from_dict(data):
        if isinstance(data, str):
            return Author(data)
        return Author(data.get('name', 'Unknown'), data.get('nationality', 'Unknown'))

class LibraryItem:
    """Base class for all library resources."""
    def __init__(
        self,
        item_id,
        title,
        location,
        press_org="Unknown",
        quantity=1,
        is_available=True,
        due_date=None,
        penalty=0.0
    ):
        self.item_id = str(item_id)
        self.title = title
        self.location = location
        self.press_org = press_org

        self._quantity = 1
        self._is_available = True
        self._due_date = None
        self._penalty = 0.0

        self.quantity = quantity
        self.is_available = is_available
        self.due_date = due_date
        self.penalty = penalty

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        value = int(value)
        if value < 1:
            raise ValueError("Quantity must be at least 1")
        self._quantity = value

    @property
    def is_available(self):
        return self._is_available

    @is_available.setter
    def is_available(self, value):
        self._is_available = bool(value)

    @property
    def due_date(self):
        return self._due_date

    @due_date.setter
    def due_date(self, value):
        if value in (None, ""):
            self._due_date = None
            return
        value = str(value)
        datetime.strptime(value, "%Y-%m-%d")  # validate format
        self._due_date = value

    @property
    def penalty(self):
        return self._penalty

    @penalty.setter
    def penalty(self, value):
        value = float(value)
        if value < 0:
            raise ValueError("Penalty cannot be negative")
        self._penalty = value

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "title": self.title,
            "location": self.location,
            "press_org": self.press_org,
            "quantity": self.quantity,
            "is_available": self.is_available,
            "due_date": self.due_date,
            "penalty": self.penalty,
            "item_type": self.__class__.__name__
        }

class Book(LibraryItem):
    def __init__(self, item_id, title, location, author, isbn, subject, press_org="Unknown", quantity=1, **kwargs):
        super().__init__(item_id, title, location, press_org, quantity, **kwargs)
        self.author = author if isinstance(author, Author) else Author.from_dict(author)
        self.isbn = isbn
        self.subject = subject

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "author": self.author.to_dict(),
            "isbn": self.isbn,
            "subject": self.subject
        })
        return data

class Periodical(LibraryItem):
    def __init__(self, item_id, title, location, issue_number, press_org="Unknown", quantity=1, **kwargs):
        super().__init__(item_id, title, location, press_org, quantity, **kwargs)
        self.issue_number = issue_number

    def to_dict(self):
        data = super().to_dict()
        data.update({"issue_number": self.issue_number})
        return data

class Newspaper(LibraryItem):
    def __init__(self, item_id, title, location, publish_date, press_org="Unknown", quantity=1, **kwargs):
        super().__init__(item_id, title, location, press_org, quantity, **kwargs)
        self.publish_date = str(publish_date)

    def to_dict(self):
        data = super().to_dict()
        data.update({"publish_date": self.publish_date})
        return data

class Multimedia(LibraryItem):
    def __init__(self, item_id, title, location, format_type, press_org="Unknown", quantity=1, **kwargs):
        super().__init__(item_id, title, location, press_org, quantity, **kwargs)
        self.format_type = format_type

    def to_dict(self):
        data = super().to_dict()
        data.update({"format_type": self.format_type})
        return data

class Person:
    def __init__(self, p_id, name, role, borrowed_item_ids=None):
        self.p_id = str(p_id)

        self._name = ""
        self._role = ""
        self.name = name
        self.role = role

        self._borrowed_item_ids = list(borrowed_item_ids) if borrowed_item_ids else []
        self._borrowed_items = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = str(value).strip()
        if not value:
            raise ValueError("Name cannot be empty")
        self._name = value

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, value):
        value = str(value).strip()
        if not value:
            raise ValueError("Role cannot be empty")
        self._role = value

    @property
    def borrowed_items(self):
        return tuple(self._borrowed_items)   # read-only view

    @property
    def borrowed_item_ids(self):
        return tuple(self._borrowed_item_ids)  # read-only view

    @property
    def borrow_count(self):
        return len(self._borrowed_items)

    def has_item(self, item_id):
        item_id = str(item_id)
        return any(item.item_id == item_id for item in self._borrowed_items)

    def link_borrowed_item(self, item):
        """Used when rebuilding objects from database."""
        if not self.has_item(item.item_id):
            self._borrowed_items.append(item)
        if item.item_id not in self._borrowed_item_ids:
            self._borrowed_item_ids.append(item.item_id)

    def add_borrowed_item(self, item, limit):
        if self.has_item(item.item_id):
            raise ValueError("User already borrowed this item")
        if self.borrow_count >= limit:
            raise ValueError("Borrowing limit reached")

        self._borrowed_items.append(item)
        self._borrowed_item_ids.append(item.item_id)

    def remove_borrowed_item(self, item_id):
        item_id = str(item_id)
        self._borrowed_items = [i for i in self._borrowed_items if i.item_id != item_id]
        self._borrowed_item_ids = [i for i in self._borrowed_item_ids if i != item_id]

    def replace_borrowed_item(self, old_item_id, new_item):
        old_item_id = str(old_item_id)
        self._borrowed_items = [
            new_item if i.item_id == old_item_id else i
            for i in self._borrowed_items
        ]
        self._borrowed_item_ids = [
            new_item.item_id if i == old_item_id else i
            for i in self._borrowed_item_ids
        ]

    def get_total_penalty(self):
        return sum(float(item.penalty) for item in self._borrowed_items)

    def to_dict(self):
        return {
            "p_id": self.p_id,
            "name": self.name,
            "role": self.role,
            "borrowed_item_ids": list(self.borrowed_item_ids)
        }

    @staticmethod
    def from_dict(data):
        return Person(
            data['p_id'],
            data['name'],
            data['role'],
            data.get('borrowed_item_ids', [])
        )
