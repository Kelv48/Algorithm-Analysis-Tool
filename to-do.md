- Identify inputs that the tool cannot reliably handle and that are explicitly out of scope for evaluation.
- Assess, given the current analysis machinery, how useful the tool will be for students in educational settings.
- Document how operations and events are being counted during analysis.
- Characterize computational complexity across a representative range of input sizes and patterns.
- Define input configuration parameters, including:
    - Determine typical list lengths to support.
    - Specify how input data is generated.
    - Decide on the number of iterations to run per experiment.

- Performance over multiple input sizes
- Algorithm Efficiency
- Export/Report
- Custom algorithm input (i.e allow users to enter their own code)

- Implement a bigO complexity check using the multi runs
    - Could use the same arrays and show N, nlogn, n^2, n! etc and show the algo you ran and where it falls within these baselines

- Fix issue with dfs
- Allow step through history of graph algos
    - Dont show the graph
- Add in matrix algo and generation method
- For multi gen allow users to pick different options and take the dot product of them as our different configurations, will be the amount of workers
    - If the amount of works is above a certain amount assign jobs an id and create a queue where we can pass jobs into the workers as they are freed
    - Then maintiain track of jobs in the queue to show a progress bar of jobs waiting to execute (i.e, jobs waiting to execute)
    - Pass the id into run ast and return it with the result so that we have a way of mapping outputs in a useful way (i.e, if we run merge and bubble) only compare the ones that used the same list
    - Also if we pick 2 different algos for each of the generation choices use that list on all the possible algos (i.e, if we choose merge/bubble and random/edge with 2 different options for ranges we want 4 lists to be created and each algo to be ran on each of the 4 lists and then we want each run of the same list to be sequential, so id merge[list1], id bubble[list1] and so on) 
    