import time
from worker_base import BaseWorker

class CropWorker(BaseWorker):
    def on_start(self):
        return {"name": "echo-worker", "ready": True}

    def handle(self, op, payload):
        time.sleep(1)
        return {"op": op, "echo": payload}

    def on_shutdown(self):
        return {"bye": True}

if __name__ == "__main__":
    EchoWorker().run()