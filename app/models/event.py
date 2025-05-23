def build_event_dict(data, user_email):
    now = datetime.utcnow()
    return {
        "title": data.title,
        "description": data.description,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "tags": data.tags,
        "created_by": user_email,
        "created_at": now,
        "updated_at": now,
    }
