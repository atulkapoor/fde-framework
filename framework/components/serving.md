---
id: serving
name: Serving
caps: [reasoning]
required_when:
  - output_shape == freeform
  - output_shape == classification
  - output_shape == ranking
---
Where the model actually runs, and how you pay for it.

Two independent questions decide this, and they partition differently.
**Sensitivity partitions by what**: data that cannot leave cannot be sent to a
vendor, and an embedding is not an exception -- it is recoverable to its source,
so sending one is sending the text. **Economics partitions by when**: a cold
start is a user-experience problem only while somebody is waiting, and batch
work that pays nothing between jobs is far cheaper than per-token pricing.

They co-occur, and the expensive quadrant is sensitive plus interactive. Most
of the design work is keeping out of it whatever did not need to be there.
