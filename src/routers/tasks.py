from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.postgresdb import PostgresDB
from authorization.token_based import get_current_user
from uuid import uuid4

router = APIRouter(prefix='/sqldb', tags=["tasks"])


class Task(BaseModel):
    userid : str
    task_name : str 
    task_description : str 
    start_time : int
    end_time : int
    color : str
    status : str
    priority : int

    

@router.post("/tasks/")
def create_task(task: Task, current_user = Depends(get_current_user)):
    task_info = task.dict()
    with PostgresDB() as db:
        result = db.insert("tasks", task_info)
    if result:
        return {"message": "✅ Task created!", "task":task}
    raise HTTPException(status_code=400, detail="❌ Could not create user.")


@router.get("/tasks/{user_id}")
def get_user_by_id(user_id: str,current_user = Depends(get_current_user)):
    with PostgresDB() as db:
        result = db.select("tasks", {"userid": user_id})
    if result:
        return {
            "userid": user_id,
            "tasks": result
        }
    else:
        return {
            "userid":user_id,
            "tasks": []
        }


@router.delete("/tasks/{user_id}/{task_id}")
def delete_task(user_id: str, task_id: str,current_user = Depends(get_current_user)):
    with PostgresDB() as db:
        result = db.execute(
            "DELETE FROM tasks WHERE userid = %s AND taskid = %s RETURNING *",
            (user_id, task_id),
            fetch_one=True,
            commit=True
        )

    if result:
        return {"message": "✅ Task deleted!", "task": result}
    raise HTTPException(status_code=404, detail="❌ Task not found.")
