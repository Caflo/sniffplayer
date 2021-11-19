import json
from bson.objectid import ObjectId

from sniffplayer import sniffer


class TaskDBHandler:
    def __init__(self, db) -> None:
        self.db = db

    # CRUD methods

    def create(self, task):
        task = sniffer.SnifferTask(iface=task.iface, active=task.active, dynamic=task.dynamic, schedule=task.schedule)
        task_json = json.loads(json.dumps(task, default=lambda o: o.__dict__, sort_keys=True, indent=4))
        return self.db.tasks.insert_one(task_json)  # returns _id

    def read_all(self):
        tasks = self.db.tasks.find({})
        return tasks
    
    def read_by_id(self, id):
        task = self.db.tasks.find_one({"_id": ObjectId(id)})
        return task

    def update(self, task):
        self.db.tasks.update_one({"_id": ObjectId(task['_id'])}, { "$set": 
                                            {
                                                "iface": task['iface'],
                                                "active": task['active'],
                                                "dynamic": task['dynamic'],
                                                "thread_id": task['thread_id'],
                                                # TODO ALSO schedule
                                            }})

    def delete(self, id):
        # TODO add check for active tasks, must stop the thread before deleting them
        self.db.tasks.delete_one({"_id": ObjectId(id)})