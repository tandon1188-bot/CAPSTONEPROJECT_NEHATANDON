try:
    from google.cloud import pubsub_v1
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(GCP_PROJECT_ID, "user-events")
    except Exception as e:
        print(f"Pub/Sub not configured: {e}")
        publisher = None
except ImportError:
    publisher = None
from app.config import GCP_PROJECT_ID




# #def publish_event(event_name: str, data: dict):
#     import json
#     message_json = json.dumps({"event": event_name, "data": data})
#     message_bytes = message_json.encode("utf-8")
#     publisher.publish(topic_path, data=message_bytes)

def publish_event(topic: str, message: dict):
    if publisher:
        # actual publish code
        pass
    else:
        print(f"Skipping Pub/Sub publish for topic {topic}")