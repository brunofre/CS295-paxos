# PAXOS

This is a paxos implementation for CS 295 Blockchain class.

## Usage

## Usage
```

python3 paxos.py method ip port --coordip IP --coordport PORT --attack TYPE --enable-middleware

```

Choose a method between node (needs --coord*), coordinator, demo.

--attack can be used with a node or with demo, can be LIVENESS or SAFETY.
--enable-middleware enables middleware to protect against both attacks



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




## Malicious attacks

### SAFETY:

Assume there are $2n + 1$ nodes. Except the malicious node $M$, all other nodes are honest. Assume a fresh start.

  1. $M$ sends `prepare(b)` to all nodes.
  2. After receiving $n$ amount of `prepared` messages, $M$ sends `propose(b, va)` to $n$ nodes and `propose(b, vb)` to another $n$ nodes, where $v_a \neq v_b$.
  3. As a result, $n$ nodes accept $v_a$ and $n$ nodes accept $v_b$.

> Solution:
> Nodes can broadcast every propose they receive to the other nodes. If any mismatch happens (for the same position), then we know the node is acting maliciously.

### LIVENESS:

Assume there's a malicious node $M$. Everytime $M$ receives a prepare message `prepare(b)`, it always immediately sends a prepare message `prepare(b')` with a $b' > b$ to all nodes and ignore the `prepared` message. In this case, all other nodes will not respond to `prepare(b)` since they have got `prepare(b')`.

> Solution:
> Ban a node if it refused to respond to a `prepared` message too many times.

### Other attacks

These are some extra attacks for reference only.

#### **P**artition tolerance

Paxos cannot tolerate partition even without malicious node.

#### Prepare phase

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

Instead of sending a previously prepared value, malicous node send its own value ignoring the previous one.

> Solution:
> When nodes send an accept(b, v), it should be also broadcast to every other node not only to the leader. The other node's middleware will ignore any propose(b, v') with same ballot but v' != v.

### Accept phase

### Commit phase

#### Attack 1 (safety):

Malicious leader send `commit` after his proposal is accepted before he receive accept message from the majority.

> Solution:
> The inform message should include all accept messages.


