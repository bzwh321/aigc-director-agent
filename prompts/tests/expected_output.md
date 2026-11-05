# Expected behavior

The agent must return `GRILL_ME`, not a final Seedance prompt.

The first failed gate is G1 because start and end states are not explicit. The next question batch should ask for the start state, end state, and intended narrative state change before discussing workflow nodes or paid generation.
