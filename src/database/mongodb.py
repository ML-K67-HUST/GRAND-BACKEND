import pymongo
import json
from bson import ObjectId
from config import settings

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)
    
class MongoManager:
    __instances = {}

    def __new__(cls, db):
        if db not in cls.__instances:
            cls.__instances[db] = super().__new__(cls)
            cls.__instances[db].__initialized = False
        return cls.__instances[db]

    def __init__(self, db):
        if self.__initialized:
            return
        self.__initialized = True

        self.db = db
        self.connection_str = settings.mongodb_url
        self.__client = pymongo.MongoClient(self.connection_str)
        self.__database = self.__client[self.db]

    # Inserts a single document into the specified collection
    def insert_one(self, collection_name, data):
        collection = self.__database[collection_name]
        collection.insert_one(data)

    # Inserts multiple documents into the specified collection
    def insert_many(self, collection_name, data, options={}):
        collection = self.__database[collection_name]
        collection.insert_many(data, **options)

    # Performs a bulk upsert (update or insert) operation on the specified collection
    def upsert_many(self, collection_name, data):
        collection = self.__database[collection_name]
        collection.bulk_write(data)

    # Updates a single document in the specified collection based on a filter
    def update_one(self, collection_name, filter, data):
        collection = self.__database[collection_name]
        collection.update_one(filter, data, upsert=True)

    # Updates multiple documents in the specified collection based on a filter
    def update_many(self, collection_name, filter, data):
        collection = self.__database[collection_name]
        collection.update_many(filter, data)

    # Deletes multiple documents in the specified collection based on a filter
    def delete_many(self, collection_name, filter={}):
        collection = self.__database[collection_name]
        collection.delete_many(filter)

    # Finds a single document in the specified collection based on a filter
    def find_one(self, collection_name, filter={}):
        collection = self.__database[collection_name]
        return collection.find_one(filter)

    # Finds multiple documents in the specified collection based on a filter, with optional projection, sorting, offset, and limit
    def find(
        self,
        collection_name,
        filter={},
        projection=None,
        sort=None,
        offset=0,
        limit=None,
    ):
        collection = self.__database[collection_name]
        result = collection.find(filter, projection)
        if sort:
            result = result.sort(*sort)
        if offset:
            result = result.skip(offset)
        if limit:
            result = result.limit(limit)
        return list(result)

    # Performs an aggregation operation on the specified collection
    def aggregate(self, collection_name, filter={}):
        collection = self.__database[collection_name]
        return collection.aggregate(filter)

    # Finds the distinct values for a specified field across a single collection and returns the list of distinct values
    def distinct(self, collection_name, field, filter={}):
        collection = self.__database[collection_name]
        return collection.distinct(field, filter)
