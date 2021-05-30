# PAXOS

This is a paxos implementation for CS 295 Blockchain class.

## Usage

```
python paxos.py
```

## Structure


* `paxos.py`:
* `coordinator.py`:
* `node.py`:
* `messages.py`:
  * `Message`:
    * `PrepareMessage`
    * `PreparedMessage`
    * `ProposeMessage`
    * `AcceptMessage`
  * `CoordinatorMessage`:
    * `PeerInfo`
    * `DebugInfo`
    * `CoordinatorExitCommand`
    * `CoordinatorPropagateMessage`

## Malicious attack (CAP)



### Consistency

* Problem: Assume there are $n = 2m + 1$ nodes. $2m$ of them are honest. There's no previous accepted proposal.
  1. malicious party send prepare message with ballot $b$ to all nodes.
  2. After receiving $m$ prepared messages, malicious party send propose message with ballot $b$ and value $v_a$ to $m$ nodes, $v_b$ to another $m$ nodes.
  3. As a result, $m$ of the nodes accept $v_a$ and $m$ of the nodes accept $v_b$.

* Solution:
  * Nodes need to broadcast their status to other node as what PBFT does?

### Availability



### Partition tolerance


### Prepare phase

* Problem: Malicious node prepare a maximum int as ballot number.
  * The difference between ballot numbers cannot be larger than $n$?

* Problem: Malicious node prepare replay other nodes' prepare message.
  * The ballot number is protected by signature, the ballot will be ignore if it is not the largest. This attack cannot success.

### Prepared phase

* Problem: malicious node didn't send the latest proposal.
  * The majority should send the latest proposal back, so this attack cannot success.

### Propose phase

* Problem: instead of sending a previously accepted value, malicous node send its own value with a higher ballot number.
  * A honest node should reject any proposal which has different value than previously accept one.

### Accept phase

* Problem: malicious leader tells everyone his proposal is accepted  before he receive accept message from the majority.
  * The inform message should include all accept messages.


