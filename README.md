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



