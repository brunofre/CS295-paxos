# PAXOS

This is a paxos implementation for the CS 295 Blockchain class at UCI in Spring 2021.

## Implementation:

Our implementation consists mainly of two parts: the coordinator and the nodes. These can be run completely independently, see Usage below.

### Coordinator

Is responsible for coordinating the nodes but is not part of the Paxos instance itself. To join the Paxos instance, every node will connect initially to the Coordinator, which will store public keys and (ip,port) pairs for the actual paxos messages between nodes. This avoids the need for each node to have a hardcoded (pkey, ip, port) for each other node, all a node needs to join Paxos is the address of the Coordinator. We use a simple TCP connection for Coord <-> Node communication and assume it is secure. Note that in deployment this should be replaced by SSL, we skip this part so as to not bother with certificates etc. At this initial connection a debug TCP socket is initialized so that nodes can send debug messages to the Coordinator. This socket is also used so that the coordinator can be used as a client, requesting nodes try to propagate a specific value. At deployment this could be used so that clients need not know any node's address, only the coordinator's.

### Node

After connecting to the coordinator and getting the other node's information (namely verifying key, ip and UDP port) we can start the actual paxos protocol. Messages are signed using ECDSA but otherwise the protocol follows paxos using UDP so that packet dropping/delays are simply ignored by the node.

## Usage
```

python3 paxos.py method ip port --coordip IP --coordport PORT --attack TYPE --middleware

```

Choose a method between node (needs --coord*), coordinator (ignores --coord*), demo (takes only the --attack and --middleware parameters).

--attack can be used with a node or with demo, can be LIVENESS or SAFETY.

--middleware enables middleware to protect against both attacks


## Structure


* `paxos.py`: implements __main__
* `coordinator.py`: implements the Coordinator
* `node.py`: implements the Node, malicious if --attack set and using the middleware if --middleware
* `messages.py`: implements the messages that are sent Node <-> Node and Node <-> Coordinator


## Malicious attacks (see --attack)

### SAFETY:

Assume there are 2n + 1 nodes. Except the malicious node M, all other nodes are honest. Assume a fresh start.

  1. M sends `prepare(b)` to all nodes.
  2. After receiving n amount of `prepared` messages, M sends `propose(b, va)` to n nodes and `propose(b, vb)` to another n nodes, where va != vb.
  3. As a result, n nodes accept va and n nodes accept vb.

> Solution (implemented in the middleware):
> Nodes can broadcast every propose they receive to the other nodes. If any mismatch happens (for the same position), then we know the node is acting maliciously.

### LIVENESS:

Assume there's a malicious node M. Everytime M receives a prepare message `prepare(b)`, it always immediately sends a prepare message `prepare(b+1)` to all nodes and ignores the `prepared` messages received back. In this case, all the other nodes will not respond to `prepare(b)` since they have got `prepare(b+1)`.

> Solution (implemented in the middleware):
> Ignore a node if it tried to `prepare` too many times for the same position.

For demo purposes we set the number of max prepares to 3. In actual deployment we should improve this condition, possibly taking into account the timestamp of the prepares, network conditions and how many nodes there are.

### Other attacks (not implemented)

These are some extra attacks for reference only.

#### Liveness 2:

Malicious node send `prepare(b)` where the ballot number `b` is a maximum int then ignore all `prepared` messages. No other nodes can propose.

> Solution:
> The difference between consecutive ballot numbers should be bounded

#### Safety 2:

Instead of sending a previously prepared value (that the node received from a `prepared(b, v)` message in reply to its `prepare`), malicous node send its own value `v'`

> Solution:
> When nodes send an accept(b, v), it should be also broadcast to every other node not only to the leader. The other node's middleware will ignore any propose(b, v') with same ballot but v' != v.


#### Safety 3:

Malicious leader sends `commit` after his proposal but before he receives accept messages from the majority.

> Solution:
> The `commit` message should include all accept messages (which are signed in our implementation).


