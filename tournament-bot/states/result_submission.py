from aiogram.fsm.state import StatesGroup, State

class ResultSubmission(StatesGroup):
    screenshot = State()
    place = State()
    requisites = State()
