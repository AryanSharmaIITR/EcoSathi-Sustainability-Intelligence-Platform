from app.schemas.base import AIGeneratedResponse


class WasteClassificationResponse(AIGeneratedResponse):
    item_name: str
    category: str
    disposal_instructions: str
