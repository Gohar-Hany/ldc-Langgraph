from typing_extensions import TypedDict

# Define State 
class State(TypedDict):
    name : str
    greeting : str

# Define node
def greeting(state : State):
    return {
        "greeting" : f"Hello {state['name']}"
    }


# Build the graph
from langgraph.graph import StateGraph , START , END

builder = StateGraph(State)

# Add node
builder.add_node("greet" , greeting)

# Add edge
builder.add_edge(START,"greet")
builder.add_edge("greet", END)

# Compile the graph
graph = builder.compile()

# Invoke the graph
result = graph.invoke({
    "name"     : "Gohar",
    "greeting" :""
})

print(result)
