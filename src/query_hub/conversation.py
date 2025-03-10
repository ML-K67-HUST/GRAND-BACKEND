from database.mongodb import MongoManager


mongo_client = MongoManager("TIMENEST")

def convert_objectid(doc):
    """Chuyển đổi ObjectId trong document thành string"""
    if isinstance(doc, list):
        return [convert_objectid(d) for d in doc]
    if isinstance(doc, dict):
        doc["_id"] = str(doc["_id"])  
        return doc
    return doc

def get_conversation(userid : int):
    return convert_objectid(mongo_client.find(
        "conversation",
        {
            "userid":userid
        }
    ))

def insert_conversation(userid : int, history : dict):
    try:
        mongo_client.update_one(
            "conversation",
            {"userid": userid},
            {"$push": {"history": history}}
        )
        return {"message": "Suck seed"}
    except Exception as e:
        print('exception happened: ',e)
        return False
