# A directory for testing out project functionality

## Tree Json

Tree Json is the json taken from the ast created by 

```python
print("Hello World!")
```

From investigating if the tree can be executed without compilation I found out it doesn't seem to be possible directly \n
as a tree is just an abstract structure that represents the code in a way that is easy for the machine to modify. <br>
However it seems it may be possible to use an interpreter however this may take more effort than the benefit we get from not recompiling the code

[Link](https://astexplorer.net/) to ast explorer which shows the break down of trees for different programming languages
