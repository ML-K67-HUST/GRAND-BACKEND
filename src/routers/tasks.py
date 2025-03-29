from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.postgresdb import PostgresDB
from authorization.token_based import get_current_user
from uuid import uuid4
from typing import Optional

router = APIRouter(prefix='/sqldb', tags=["tasks"])


class Task(BaseModel):
    taskid: str = None
    userid: str
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    color: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None

class UpdateTask(BaseModel):
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    color: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None

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

@router.put("/tasks/{user_id}/{task_id}")
def update_task(user_id: str, task_id: str, task: UpdateTask, current_user = Depends(get_current_user)):
    task_info = {k: v for k, v in task.dict().items() if v is not None}
    
    if not task_info:
        raise HTTPException(status_code=400, detail="❌ No fields to update provided.")
        
    with PostgresDB() as db:
        result = db.update("tasks", task_info, {"userid": user_id, "taskid": task_id})
    if result:
        return {"message": "✅ Task updated!", "task": result}
    raise HTTPException(status_code=404, detail="❌ Task not found.")


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
