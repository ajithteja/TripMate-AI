from tools.tavily_tool import tavily_search

from backend import run_travel_agent

# res = tavily_search("Best hotels in yadagirigutta")

# print(res)


user_input = input("Enter travel request: ")



res = run_travel_agent(
    user_input,
    "test_user"
)
print(res)