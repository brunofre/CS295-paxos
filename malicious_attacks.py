from enum import Enum


class MaliciousAttacks(Enum):
    CONSISTENCY = 1
    AVILABILITY = 2
    PREPARE_PHASE_1 = 3
    PREPARE_PHASE_2 = 4
    PREPARED_PHASE = 5
    PROPOSE_PHASE = 6
    ACCEPT_PHASE = 7
