from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime, timedelta
import calendar
import os
from constants.test_data import TEST_CATEGORIES
from dotenv import load_dotenv
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
client = MongoClient(MONGODB_URL)
model = SentenceTransformer('all-MiniLM-L6-v2')

def categorize_task(task):
    category_embeddings = {}
    for category, examples in TEST_CATEGORIES.items():
        category_embeddings[category] = model.encode(category + ": " + ", ".join(examples))

    task_embedding = model.encode(task)
    similarities = {}
    for category, category_embedding in category_embeddings.items():
        similarity = cosine_similarity([task_embedding], [category_embedding])[0][0]
        similarities[category] = similarity
    
    best_category = max(similarities, key=similarities.get)
    return best_category

def get_user_information(client, mode: str = "week", user_id: str = ''):
    db = client.Timenest
    tasks_collection = db.tasks
    now = datetime.now()
    start_of_time = now 
    end_of_time = now

    if mode ==  'week': 
        start_of_time = now - timedelta(days=now.isoweekday() - 1)
        end_of_time = start_of_time + timedelta(days=6)
    if mode == 'month': 
        start_of_time = now.replace(day=1)
        last_day_of_month = calendar.monthrange(now.year, now.month)[1]
        end_of_time = now.replace(day=last_day_of_month)

    tasks = tasks_collection.find({
        "userID": user_id,
        "startTime": {
            "$gte": start_of_time.isoformat() + 'Z', 
            "$lte": end_of_time.isoformat() + 'Z'
        }
    })

    users_task_analysist = [{
        'user_id': 1,
        'hours': 0, #Tong so gio lam viec trong tuan/thang
        'tasks': [], # Before mapping, day is the earliest start day of the task.
        'categories': [] #After mapping, remove day.
    }]

    for task in tasks: 
        user_id = task['userID']
        task_name = task['taskName']
        start_time = task['startTime']
        end_time = task['endTime']
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        spend_time = end_time - start_time 
        task_hours = spend_time.total_seconds()/3600

        user_found = False
        for user_task in users_task_analysist:
            if user_task['user_id'] == user_id:
                user_task['hours'] += task_hours  
                exist = 0
                for subtask in user_task['tasks']:
                    if subtask[0] ==  task_name: 
                        subtask[1] += task_hours
                        exist = 1
                if exist == 0: 
                    user_task['tasks'].append([task_name, task_hours, str(start_time)])
                user_found = True
                break
        
        # If the user is not found in the list, create a new user entry
        if not user_found:
            users_task_analysist.append({
                'user_id': user_id,
                'hours': task_hours,
                'tasks': [([task_name, task_hours, str(start_time)])],
                'categories': []
            })

    users_task_analysist = users_task_analysist[1:]

    for user in users_task_analysist:
        for task in user['tasks']: 
            map_category = categorize_task(task[0])  
            existed = 0 
            for cate in user['categories']: 
                if map_category == cate[0]: 
                    cate[1] += task[1]
                    existed = 1 
            if existed == 0: 
                user['categories'].append([map_category, task[1]])

    return users_task_analysist
import matplotlib.pyplot as plt
import numpy as np

def draw_radar_chart(data):
    categories = [item[0] for item in data[0]['categories']]
    values = [item[1] for item in data[0]['categories']]

    num_vars = len(categories)

    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]

    values += values[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

    ax.plot(angles, values)

    ax.fill(angles, values, alpha=0.25)

    plt.xticks(angles[:-1], categories)

    ax.set_rlabel_position(0)
    max_value = max(values)
    plt.yticks(np.arange(1, max_value + 1, 2), color="grey", size=7)
    plt.ylim(0, max_value)

    plt.title(f"User {data[0]['user_id']} Activity Radar Chart", size=20, y=1.1)

    plt.tight_layout()
    # plt.savefig('taxonomy.jpg')
    plt.show()
    return
if __name__ == '__main__':
    print(draw_radar_chart(get_user_information(client=client,user_id='109356546733291536481')))