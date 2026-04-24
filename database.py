import os
import pymongo
from models import LogEntry


class DBManager:
    def __init__(self, uri=None):
        self._uri = uri or os.getenv("MONGODB_URI")
        if not self._uri:
            raise ValueError("MONGODB_URI is not configured")

        try:
            self._client = pymongo.MongoClient(self._uri)
            self._db = self._client['LibrarySystemDB']

            self._items_col = self._db['items']
            self._people_col = self._db['people']
            self._logs_col = self._db['logs']

            print("Successfully connected to MongoDB Atlas!")
        except Exception as e:
            raise ConnectionError(f"Database connection failed: {e}")

    def load_items_raw(self):
        return list(self._items_col.find({}, {'_id': 0}))

    def save_item(self, item):
        item_data = item.to_dict()
        self._items_col.update_one(
            {"item_id": str(item.item_id)},
            {"$set": item_data},
            upsert=True
        )

    def delete_item(self, item_id):
        self._items_col.delete_one({"item_id": str(item_id)})

    def load_people_raw(self):
        return list(self._people_col.find({}, {'_id': 0}))

    def save_person(self, person):
        person_data = person.to_dict()
        self._people_col.update_one(
            {"p_id": str(person.p_id)},
            {"$set": person_data},
            upsert=True
        )

    def delete_person(self, p_id):
        self._people_col.delete_one({"p_id": str(p_id)})

    def add_log(self, log_entry):
        self._logs_col.insert_one(log_entry.to_dict())

    def load_logs(self):
        raw_logs = self._logs_col.find().sort("timestamp", -1)
        logs = []
        for l in raw_logs:
            entry = LogEntry(
                action=l.get('action'),
                item_title=l.get('item_title'),
                person_name=l.get('person_name'),
                log_id=l.get('log_id'),
                timestamp=l.get('timestamp')
            )
            logs.append(entry)
        return logs
