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

## Malicious attack on CAP

### Usage

Set the type of attacks in `paxos.py`
```
attack = Attack.COMMIT_PHASE
```
Set `attack` to `None` if no attacks selected.

### **C**onsistency
#### Attack 1 (safety):

Assume there are $2n + 1$ nodes. Except the malicious node $M$, all other nodes are honest. Assume a fresh start.

  1. $M$ sends `prepare(b)` to all nodes.
  2. After receiving $n$ amount of `prepared` messages, $M$ sends `propose(b, va)` to $n$ nodes and `propose(b, vb)` to another $n$ nodes, where $v_a \neq v_b$.
  3. As a result, $n$ nodes accept $v_a$ and $n$ nodes accept $v_b$.

> Solution:
> Nodes can broadcast their status to other node as what PBFT does.



### **A**vailability
#### Attack 1 (liveness):

Assume there's a malicious node $M$. Everytime $M$ receives a prepare message `prepare(b)`, it always immediately sends a prepare message `prepare(b')` with a $b' > b$ to all nodes and ignore the `prepared` message. In this case, all other nodes will not respond to `prepare(b)` since they have got `prepare(b')`.

> Solution:
> Ban a node if it refused to respond to a `prepared` message too many times.

### **P**artition tolerance

Paxos cannot tolerate partition even without malicious node.


## General malicious behavior

### Prepare phase

#### Attack 1 (liveness):

Malicious node send `prepare(b)` where the ballot number `b` is a maximum int then ignore all `prepared` messages. No other nodes can propose.

> Same as https://stackoverflow.com/questions/19240919/how-do-you-mitigate-proposal-number-overflow-attacks-in-byzantine-paxos

> Solution:
> The difference between ballot numbers cannot be larger than $n$?

### Prepared phase

#### Attack 1 (liveness):

Malicious node didn't send the latest proposal.

> Solution:
> The majority should send the latest proposal back, so this attack cannot success.
> However, when there're only 3 nodes, there's no way to prevent this attack.

### Propose phase

#### Attack 1 (safety):

Instead of sending a previously accepted value, malicous node send its own value instead of the previously proposed one.

> Solution:
> A honest node should reject any proposal which has different value from the previously accepted one.

### Accept phase

### Commit phase

#### Attack 1 (safety):

Malicious leader send `commit` after his proposal is accepted before he receive accept message from the majority.

> Solution:
> The inform message should include all accept messages.


