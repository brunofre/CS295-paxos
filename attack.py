from enum import Enum


class Attack(Enum):

    NONE = 0

    # sends distinct propagates: half of the nodes will get X
    # and the other half gets X || "safety attack"
    SAFETY = 1

    # ballot climbing attack: every time we receive
    #   a prepare we try to prepare ballot + 1
    LIVENESS = 2

    PREPARE_PHASE = 3
    PREPARED_PHASE = 4
    
    # ignore values from prepared messages, forcing our own
    #   value to propagate
    IGNORE_PREPARED = 5

