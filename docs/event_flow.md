## transaction event flow

### events
We need 6 events.<br>
These should be something like: <br>
a: fraud detection checks book order<br>
b: fraud detection checks if user data is fraudulent<br>
c: verification service verifies card info<br>
d: verification service confirms card has enough money<br>
e: suggestions service sends a request for suggestions<br>
f: verification service initiates payment<br>


### event ordering
event order could be something like this:<br>
a, b > c > d > f<br>
c > e<br>
Where a > b means that b should start after a has completed.<br>
Orchestrator gets the result when all events have completed or an error occurs