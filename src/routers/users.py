from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.postgresdb import PostgresDB
from uuid import uuid4
from authorization.token_based import get_current_user
router = APIRouter(prefix='/sqldb', tags=["users"])


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str


class UserUpdate(BaseModel):
    email: str 
    password: str
    full_name: str 


@router.post("/users/")
def create_user(user: UserCreate, current_user = Depends(get_current_user) ):
    user_info = user.dict()
    with PostgresDB() as db:
        result = db.insert("users", user_info)
        user = db.select("users", {"username": user_info["username"]})
    if result:
        print(result)
        print(user)
        return {"message": "✅ User created!", "user": user[0]}
    raise HTTPException(status_code=400, detail="❌ Could not create user.")


@router.get("/users/{user_id}")
def get_user_by_id(user_id: str,current_user = Depends(get_current_user)):
    with PostgresDB() as db:
        result = db.select("users", {"userid": user_id})
    if result:
        return {"user": result[0]}
    raise HTTPException(status_code=404, detail="❌ User not found.")


@router.get("/users/")
def get_all_users(current_user = Depends(get_current_user)):
    with PostgresDB() as db:
        result = db.select("users")
    return {"users": result} if result else {"message": "No users found."}


@router.put("/users/{user_id}")
def update_user(user_id: str, user: UserUpdate,current_user = Depends(get_current_user)):
    user_data = user.dict(exclude_unset=True)
    if not user_data:
        raise HTTPException(status_code=400, detail="❌ No data to update.")

    set_clause = ", ".join(f"{k} = %s" for k in user_data.keys())
    query = f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *"
    
    with PostgresDB() as db:
        result = db.execute(query, list(user_data.values()) + [user_id], fetch_one=True, commit=True)

    if result:
        return {"message": "✅ User updated!", "user": result}
    raise HTTPException(status_code=404, detail="❌ User not found.")


@router.delete("/users/{user_id}")
def delete_user(user_id: str,current_user = Depends(get_current_user)):
    with PostgresDB() as db:
        result = db.execute("DELETE FROM users WHERE id = %s RETURNING *", (user_id,), fetch_one=True, commit=True)

    if result:
        return {"message": "✅ User deleted!", "user": result}
    raise HTTPException(status_code=404, detail="❌ User not found.")
