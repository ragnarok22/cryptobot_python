from dataclasses import dataclass


@dataclass
class App:
    app_id: int
    name: str
    payment_processing_bot_username: str
