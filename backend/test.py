from app.tools.read_tools import search_logs
print(search_logs.invoke({"service": "payment-service"}))