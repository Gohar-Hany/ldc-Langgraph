from typing_extensions import TypedDict

class State(TypedDict):
    name : str
    greeting : str

def greeting(state : State):
    return {
        "greeting" : f"Hello {state['name']}"
    }



from langgraph.graph import StateGraph , START , END

builder = StateGraph(State)

builder.add_node("greet" , greeting)

builder.add_edge(START,"greet")
builder.add_edge("greet", END)

graph = builder.compile()

result = graph.invoke({
    "name"     : "Gohar",
    "greeting" :""
})

print(result)
