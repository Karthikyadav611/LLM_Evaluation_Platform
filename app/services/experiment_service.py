import uuid


def create_experiment_ids() -> tuple[str, str]:
    return str(uuid.uuid4()), str(uuid.uuid4())
