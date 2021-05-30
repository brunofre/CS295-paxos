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

