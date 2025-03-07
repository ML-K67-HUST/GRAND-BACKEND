

from database.mongodb import MongoManager
from config import settings
import hashlib

mongo_client = MongoManager(settings.mongodb_timenest_db_name)
def check_login(username, password):
    if mongo_client.find_one('users', {'UserName': username}):
        if mongo_client.find('users', {'UserName': username, 'Password': password}):
            user = mongo_client.find_one('users',{'UserName': username})
            userID = user['userID']
            return {
                "status": 200,
                "message": "Login successful",
                "userID": userID
            }
        else:
            return {
                "status": 200,
                "message": "Wrong password"
            }
    else:
        return {
            "status":401,
            "message": 'User not found, would you like to create an account?'
        }

def create_account(
    username,
    password,
    confirm_password
):
    if not username or not password or not confirm_password:
        return {
            "status": 400,
            "error": "All fields are required"
        }
    
    if password != confirm_password:
        return {
            "status":400,
            "error": "Passwords do not match"
        }

    if mongo_client.find_one('users', {"UserName": username}):
        return {
            "status":400,
            "error": "Username already exists"
        }
    userID = hashlib.md5("your_string_here".encode()).hexdigest()[:8](username)

    # insert vao db 

    # mongo_client.insert_one(
    #     'users', 
    #     {
    #         "userid": userID,
    #         "username": username, 
    #         "password": password
    #     }
    # )
    return {
        "status": 201,
        "message": "Account created successfully"
    }

def get_user_metadata(userID):
    try:
        metadata = mongo_client.find(
            "users",
            {
                "userid":userID
            }
        )
        return {
            "status":200,
            "message":{
                "metadata":metadata
            }
        }
    except Exception as e:
        return {
            'status':500,
            'message':f'Internal server error: {e}'
        }