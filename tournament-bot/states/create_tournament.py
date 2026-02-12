from aiogram.fsm.state import StatesGroup, State

class CreateTournament(StatesGroup):
    title = State()
    max_players = State()
    entry_fee = State()
    prize_places = State()
    prizes = State()
