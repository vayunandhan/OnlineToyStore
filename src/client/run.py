import sys
from threading import Thread
from client import ToyStoreClient

debugger_logs = True

clients_count = int(sys.argv[1])
requests_count = int(sys.argv[2])
max_buy = int(sys.argv[3])
buy_prob = float(sys.argv[4])
host = sys.argv[5]

# client threads and clients
client_threads = []
clients = []

# initialising the client instances and assigning to thread to serve
for _index in range(clients_count):
    name = 'Client {}'.format(_index)
    client = ToyStoreClient(name, requests_count, buy_prob, max_buy)
    clients.append(client)
    client_thread = Thread(target=client.serve, name=name, args=(host,), daemon=True)
    client_thread.start()
    client_threads.append(client_thread)

# terminating threads
for client_thread in client_threads:
    client_thread.join()

# calculating the average responses
qry_avg_response_for_each_client = []
buy_avg_response_for_each_client = []
existing_buy_avg_response_for_each_client = []
for client in clients:
    # Query Requests
    response_times = client.query_response_times
    if debugger_logs:
        print("client:", client.name, )
        print("Response times", response_times)
    qry_avg_response = 0 if len(response_times) == 0 else sum(response_times) / len(response_times)
    qry_avg_response_for_each_client.append(qry_avg_response)
    if debugger_logs:
        print("Average Query response:", qry_avg_response)

    # Buy Requests
    response_times = client.order_response_times
    if debugger_logs:
        print("client:", client.name, )
        print("Response times", response_times)
    buy_avg_response = 0 if len(response_times) == 0 else sum(response_times) / len(response_times)
    buy_avg_response_for_each_client.append(buy_avg_response)
    if debugger_logs:
        print("Average response:", buy_avg_response)

    # Existing Orders
    response_times = client.existing_order_response_times
    if debugger_logs:
        print("client:", client.name, )
        print("Response times", response_times)
    existing_buy_avg_response = 0 if len(response_times) == 0 else sum(response_times) / len(response_times)
    existing_buy_avg_response_for_each_client.append(existing_buy_avg_response)
    if debugger_logs:
        print("Average response:", existing_buy_avg_response)

overall_qry_avg_response = sum(qry_avg_response_for_each_client) / clients_count
overall_buy_avg_response = sum(buy_avg_response_for_each_client) / clients_count
overall_existing_order_avg_response = sum(existing_buy_avg_response_for_each_client) / clients_count

print("No. of clients:", clients_count)
print("Overall Query Average Response time:", overall_qry_avg_response)
print("Overall Buy Average Response time:", overall_buy_avg_response)
print("Overall Existing Order Average Response time:", overall_existing_order_avg_response)
