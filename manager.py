from datetime import datetime, timedelta
from database import DBManager
from models import Book, Periodical, Newspaper, Multimedia, Person, LogEntry, Author
from constants import BORROW_LIMITS, BORROW_DURATION, DAILY_PENALTY

class LibraryManager:
    def __init__(self):
        self._db = DBManager()
        self._items = []
        self._users = []
        self._history = []
        self.load_data()

    @property
    def items(self):
        return tuple(self._items)

    @property
    def users(self):
        return tuple(self._users)

    @property
    def history(self):
        return tuple(self._history)

    def load_data(self):
        raw_items = self._db.load_items_raw()
        raw_people = self._db.load_people_raw()

        self._users = [Person.from_dict(p) for p in raw_people]
        user_borrow_map = {p['p_id']: p.get('borrowed_item_ids', []) for p in raw_people}

        self._items = []
        for d in raw_items:
            i_type = d.get("item_type")
            item_id = str(d['item_id'])

            press_org = d.get('press_org', "Unknown")
            quantity = int(d.get('quantity', 1))
            extra_info = {
                "is_available": d.get("is_available", True),
                "due_date": d.get("due_date"),
                "penalty": float(d.get("penalty", 0.0))
            }

            if i_type == "Book":
                auth_data = d.get('author', {"name": "Unknown", "nationality": "Unknown"})
                author_obj = Author(auth_data.get('name', 'Unknown'), auth_data.get('nationality', 'Unknown'))
                obj = Book(item_id, d['title'], d['location'], author_obj, d['isbn'], d['subject'], press_org, quantity, **extra_info)
            elif i_type == "Periodical":
                obj = Periodical(item_id, d['title'], d['location'], d['issue_number'], press_org, quantity, **extra_info)
            elif i_type == "Newspaper":
                obj = Newspaper(item_id, d['title'], d['location'], d['publish_date'], press_org, quantity, **extra_info)
            elif i_type == "Multimedia":
                obj = Multimedia(item_id, d['title'], d['location'], d['format_type'], press_org, quantity, **extra_info)
            else:
                continue

            current_borrower_count = 0
            for user in self._users:
                if item_id in user_borrow_map.get(user.p_id, []):
                    user.link_borrowed_item(obj)
                    current_borrower_count += 1

            obj.is_available = current_borrower_count < obj.quantity
            self._items.append(obj)

        self._history = self._db.load_logs()

    def get_item_by_id(self, item_id):
        return next((i for i in self._items if i.item_id == str(item_id)), None)

    def get_user_by_id(self, p_id):
        return next((u for u in self._users if u.p_id == str(p_id)), None)

    def _count_current_borrowers(self, item_id):
        item_id = str(item_id)
        return sum(1 for user in self._users if user.has_item(item_id))

    def calculate_penalty(self, due_date_str):
        if not due_date_str:
            return 0, 0.0
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if today > due_date:
                days_late = (today - due_date).days
                penalty = days_late * DAILY_PENALTY
                return days_late, float(penalty)
        except (ValueError, TypeError):
            pass
        return 0, 0.0

    def borrow_item(self, item_id, user_id):
        item = self.get_item_by_id(item_id)
        user = self.get_user_by_id(user_id)

        if not item:
            return "Error: Item not found."
        if not user:
            return "Error: User not found."

        if user.has_item(item.item_id):
            return f"Error: {user.name} already has a copy of '{item.title}'."

        current_borrowers = self._count_current_borrowers(item.item_id)
        if current_borrowers >= item.quantity:
            return f"Error: All {item.quantity} copies of '{item.title}' are already borrowed."

        limit = BORROW_LIMITS.get(user.role, 5)
        if user.borrow_count >= limit:
            return f"Error: {user.name} has reached the limit of {limit} items."

        days = BORROW_DURATION.get(user.role, 14)
        item.due_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        item.penalty = 0.0

        try:
            user.add_borrowed_item(item, limit)
        except ValueError as e:
            return f"Error: {e}"

        if (current_borrowers + 1) >= item.quantity:
            item.is_available = False

        self._db.save_item(item)
        self._db.save_person(user)

        log = LogEntry("BORROW", item.title, user.name)
        self._db.add_log(log)
        self._history.insert(0, log)

        return f"Success: {user.name} borrowed '{item.title}'. Due: {item.due_date}"

    def return_item(self, item_id, user_id=None):
        item = self.get_item_by_id(item_id)
        if not item:
            return "Error: Item does not exist."

        if user_id:
            user = self.get_user_by_id(user_id)
            if user and not user.has_item(item.item_id):
                user = None
        else:
            user = next((u for u in self._users if u.has_item(item.item_id)), None)

        if not user:
            return "Error: No record of this item being borrowed by this user."

        _, calculated_penalty = self.calculate_penalty(item.due_date)
        final_penalty = max(float(item.penalty), calculated_penalty)

        user.remove_borrowed_item(item.item_id)
        self._db.save_person(user)

        item.is_available = True

        current_borrowers = self._count_current_borrowers(item.item_id)
        if current_borrowers == 0:
            item.due_date = None
            item.penalty = 0.0

        self._db.save_item(item)

        log = LogEntry("RETURN", item.title, user.name)
        self._db.add_log(log)
        self._history.insert(0, log)

        msg = f"Success: '{item.title}' returned by {user.name}."
        if final_penalty > 0:
            msg += f" Penalty of ${final_penalty:.2f} processed."
        return msg

    def add_item(self, item):
        self._items.append(item)
        self._db.save_item(item)

    def delete_item(self, item_id):
        item_id = str(item_id)
        for user in self._users:
            if user.has_item(item_id):
                user.remove_borrowed_item(item_id)
                self._db.save_person(user)

        self._items = [i for i in self._items if i.item_id != item_id]
        self._db.delete_item(item_id)

    def add_user(self, person):
        self._users.append(person)
        self._db.save_person(person)

    def delete_user(self, p_id):
        user = self.get_user_by_id(p_id)
        if user:
            for item in user.borrowed_items:
                item.is_available = True
                self._db.save_item(item)

        self._users = [u for u in self._users if u.p_id != str(p_id)]
        self._db.delete_person(p_id)

    def update_item_full(self, item_id, new_cat, new_title, new_loc, new_status, extra_val,
                         author_name=None, subject=None, new_due_date=None, penalty=0.0,
                         press_org="Unknown", quantity=1):
        old_item = self.get_item_by_id(item_id)
        if not old_item:
            return False

        if new_cat == "Book":
            nat = old_item.author.nationality if isinstance(old_item, Book) else "Unknown"
            new_item = Book(item_id, new_title, new_loc, Author(author_name, nat), extra_val, subject, press_org, quantity)
        elif new_cat == "Newspaper":
            new_item = Newspaper(item_id, new_title, new_loc, extra_val, press_org, quantity)
        elif new_cat == "Periodical":
            new_item = Periodical(item_id, new_title, new_loc, extra_val, press_org, quantity)
        else:
            new_item = Multimedia(item_id, new_title, new_loc, extra_val, press_org, quantity)

        new_item.is_available = new_status
        new_item.penalty = float(penalty)
        new_item.due_date = new_due_date if new_due_date else old_item.due_date

        for user in self._users:
            if user.has_item(item_id):
                user.replace_borrowed_item(item_id, new_item)
                self._db.save_person(user)

        for idx, itm in enumerate(self._items):
            if itm.item_id == str(item_id):
                self._items[idx] = new_item
                break

        self._db.save_item(new_item)
        return True

    def update_user(self, p_id, new_name, new_role):
        user = self.get_user_by_id(p_id)
        if user:
            user.name = new_name
            user.role = new_role
            self._db.save_person(user)
            return True
        return False
