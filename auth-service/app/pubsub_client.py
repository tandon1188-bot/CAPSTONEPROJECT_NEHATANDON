from google.cloud import pubsub_v1
from app.config import GCP_PROJECT_ID

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(GCP_PROJECT_ID, "user-events")

def publish_event(event_name: str, data: dict):
    import json
    message_json = json.dumps({"event": event_name, "data": data})
    message_bytes = message_json.encode("utf-8")
    publisher.publish(topic_path, data=message_bytes)
