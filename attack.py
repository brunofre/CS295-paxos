from enum import Enum


class Attack(Enum):
    SAFETY = 1
    LIVENESS = 2
    PREPARE_PHASE = 3
    PREPARED_PHASE = 4
    PROPOSE_PHASE = 5
    # ACCEPT_PHASE = 6
    COMMIT_PHASE = 7
