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

### **C**onsistency
#### Attack 1:

Assume there are $2n + 1$ nodes. Except the malicious node $M$, all other nodes are honest. Assume a fresh start.

  1. $M$ sends $prepare(b)$ to all nodes.
  2. After receiving $n$ amount of $prepared$ messages, $M$ sends $propose(b, v_a)$ to $n$ nodes and $propose(b, v_b)$ to another $n$ nodes, where $v_a \neq v_b$.
  3. As a result, $n$ nodes accept $v_a$ and $n$ nodes accept $v_b$.

> Solution
> * Nodes can broadcast their status to other node as what PBFT does.



### **A**vailability
#### Attack 1:

Assume there's a malicious node $M$. Everytime $M$ receives a prepare message $prepare(b)$, it always immediately sends a prepare message $prepare(b')$ with a $b' > b$ to all nodes and ignore the $prepared$ message. In this case, all other nodes will not respond to $prepare(b)$ since they have got $prepare(b')$.

> Solution:
> * Ban a node if it refused to respond to a $prepared$ message too many times.

### **P**artition tolerance




## General malicious behavior

### Prepare phase

#### Attack 1:

Malicious node prepare a maximum int as ballot number.

> Solution:
> * The difference between ballot numbers cannot be larger than $n$?

#### Attack 2:

Malicious node prepare replay other nodes' prepare message.

> Solution:
> * The ballot number is protected by signature, the ballot will be ignore if it is not the largest. This attack cannot success.

### Prepared phase

#### Attack 1:

Malicious node didn't send the latest proposal.

> Solution:
> * The majority should send the latest proposal back, so this attack cannot success.

### Propose phase

#### Attack 1:

Instead of sending a previously accepted value, malicous node send its own value with a higher ballot number.

> Solution:
> * A honest node should reject any proposal which has different value than previously accept one.

### Accept phase

#### Attack 1:

Malicious leader tells everyone his proposal is accepted  before he receive accept message from the majority.

> Solution:
> * The inform message should include all accept messages.


