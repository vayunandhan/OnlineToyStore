import json
import os
import socket
import re
import sys

from concurrent.futures import ThreadPoolExecutor
from socket import error as socket_error

sys.path.insert(0, os.path.join(sys.path[0], '..'))

from ReadWriteLock import ReadWriteLock

# regular expressions are used to validate and map the HTTP requests
route_pattern_for_query_request = re.compile("GET /products/[A-Za-z0-9_]* HTTP/1.1")
route_pattern_for_buy_request = re.compile("POST /orders HTTP/1.1")
route_pattern_for_existing_orders_request = re.compile("GET /orders/[0-9]* HTTP/1.1")
route_pattern_for_update_cache_request = re.compile("POST /update_cache HTTP/1.1")

# response templates
response_template = """\
HTTP/1.1 {status_code} {status_message}
Content-Type: application/json; charset=UTF-8
Content-Length: {content_length}

{response_data}"""
L = len(response_template)

qry_success_response_data_format = """"data": {payload}"""
L1 = len(qry_success_response_data_format)

qry_error_response_data_format = """"error": {payload}"""
L2 = len(qry_error_response_data_format)

error_response_data_format = """"error": {payload}"""
L3 = len(error_response_data_format)

debugger_logs = True
CACHE_NOT_AVAILABLE = False  # If set to False->It Means Cache is Available, If set to True->It Means Cache is Not Available


class CachedData:
    def __init__(self):
        self.catalog_data = {}


def perform_leader_election_of_order_services(order_service_ports):
    leader_order_service_port = None
    # Checking if it can connect to the Order Services and elect the leader
    order_service_ports.sort(reverse=True)
    for cur_order_service_port in order_service_ports:
        try:
            t_s = socket.socket()
            t_s.connect((OrderHost, cur_order_service_port))
            t_s.send(bytes(json.dumps({"method_name": "health_check"}), 'utf-8'))
            response = t_s.recv(1024).decode("utf-8")  # response from Order Service
            if response == 'Success':
                t_s.close()  # Closing The Connection
                leader_order_service_port = cur_order_service_port
                break
        except Exception as e:
            print('Exception Occurred in checking the status of the order_service_port: {}'.format(cur_order_service_port), e)
    print('Current Order Service Leader: {}'.format(leader_order_service_port))
    if leader_order_service_port is None:
        return None
    # Indicating the leader elected to the order services
    for cur_order_service_port in order_service_ports:
        try:
            t_s = socket.socket()
            t_s.connect((OrderHost, cur_order_service_port))
            req_body = {"method_name": "update_leader", "leader_id": '{}'.format(leader_order_service_port)}
            t_s.send(bytes(json.dumps(req_body), 'utf-8'))
            response = t_s.recv(1024).decode("utf-8")  # response from Order Service
            if response == 'Success':
                if debugger_logs:
                    print('{} order stored the leader information'.format(cur_order_service_port))
            t_s.close()
        except Exception as e:
            print('Exception Occurred when indicating the the leader to the order service {}'.format(cur_order_service_port), e)
    return leader_order_service_port


# Initializing The Order Host
# OrderHost = os.getenv("OrderHost", "order")
OrderHost = os.getenv("OrderHost", "127.0.0.1")
# Initializing The Order Port
try:
    available_order_service_ports = [int(i) for i in sys.argv[1].split(',')]
except Exception as e:
    print('Exception Occurred in initializing the order_service_ports', e)
    sys.exit()
order_service_port = perform_leader_election_of_order_services(available_order_service_ports)
if order_service_port is None:
    print('FrontEnd Service Can\'t Process Order Requests as no Order Service is Up')
    sys.exit()


# acts as handler for the HTTP requests made by the clients
def request_processor(c, addr):
    global order_service_port
    while True:
        data = c.recv(1024)
        if not data:
            break
        data = data.decode("utf-8")
        if route_pattern_for_query_request.match(data.splitlines()[0]):  # Handles the GET request
            if debugger_logs:
                print('Received get request on route /products')
            toy_name = data.splitlines()[0].split(' ')[1].split('/')[-1]
            if CACHE_NOT_AVAILABLE or toy_name not in cached_data.catalog_data:
                if debugger_logs:
                    print('Trying to fetch Catalog data from Catalog Service')
                # Communicating with Catalog Service To Fetch Current Catalog Data
                t_s = socket.socket()
                t_s.connect((CatalogHost, catalog_service_port))
                t_s.send(bytes(json.dumps({"method_name": "get_catalog_data", "toy_name": toy_name}), 'utf-8'))
                response = eval(t_s.recv(1024).decode("utf-8"))  # response from Catalog Service
                t_s.close()  # Closing The Connection
                flag, res_data = response[0], response[1]  # successful if flag=True, else failure
                if flag:
                    cached_data.catalog_data[toy_name] = res_data
                    if debugger_logs:
                        print('Successfully fetched Catalog data from Catalog Service for toy: {}'.format(toy_name))
                        print(cached_data.catalog_data)
                else:
                    if debugger_logs:
                        print('No data from Catalog Service')
            if toy_name in cached_data.catalog_data:
                flag, payload = True, {"name": toy_name, "price": cached_data.catalog_data[toy_name]['price'],
                                       "quantity": cached_data.catalog_data[toy_name]['quantity']}
            else:
                flag, payload = False, {"code": 404, "message": "product not found"}
            if flag:  # successful, adding status 200 and toy data to the output
                response_data = '{' + qry_success_response_data_format.format(payload=payload) + '}'
                c.send(bytes(
                    response_template.format(status_code=200,
                                             status_message="OK",
                                             content_length=len(payload) + L + L1,
                                             response_data=response_data), "utf-8"))
            else:  # failed to get the data, adding status 200 and error response to the output
                response_data = '{' + qry_error_response_data_format.format(payload=payload) + '}'
                c.send(bytes(
                    response_template.format(status_code=200,
                                             status_message="OK",
                                             content_length=len(payload) + L + L2,
                                             response_data=response_data), "utf-8"))
            if debugger_logs:
                print('sent the response from get request handler')
        elif route_pattern_for_buy_request.match(data.splitlines()[0]):  # Handles the POST request
            if debugger_logs:
                print('Received post request on route /orders')
            req_bod = {"method_name": "order", "data": json.loads(data.splitlines()[-1])}
            # Communicating with Order Service
            can_be_processed = False
            t_s = socket.socket()
            try:
                t_s.connect((OrderHost, order_service_port))
                can_be_processed = True
            except socket_error as e:  # Failed to connect to the leader
                print('Exception while Connecting to the leader ', e)
                new_order_service_port = perform_leader_election_of_order_services(available_order_service_ports)
                if new_order_service_port is None:
                    if debugger_logs:
                        print('FrontEnd Service Can\'t Process Order Requests as no Order Service is Up')
                else:
                    if debugger_logs:
                        print('The Front End Service will now send requests to {}'.format(new_order_service_port))
                    order_service_port = new_order_service_port
                    t_s.connect((OrderHost, order_service_port))
                    can_be_processed = True
            except Exception as e:  # Failed at processing in the Order Leader
                print('Exception while Processing in the order service ', e)
            if can_be_processed:
                t_s.send(bytes(json.dumps(req_bod), 'utf-8'))
                response = eval(t_s.recv(1024).decode("utf-8"))  # response from Order Service
                t_s.close()
                flag, res_data = response[0], response[1]
            else:
                flag, res_data = False, {"code": 500, "message": "could not place the order right now due to Internal Server Issues"}

            payload = json.dumps(res_data)
            if flag:  # successful, adding status 200 and order data to the output
                response_data = '{' + qry_success_response_data_format.format(payload=payload) + '}'
                c.send(bytes(response_template.format(status_code=200,
                                                      status_message="OK",
                                                      content_length=len(payload) + L + L1,
                                                      response_data=response_data), "utf-8"))
            else:  # failed to place the order, adding status 200 and error response to the output
                response_data = '{' + qry_error_response_data_format.format(payload=payload) + '}'
                c.send(bytes(response_template.format(status_code=200,
                                                      status_message="OK",
                                                      content_length=len(payload) + L + L2,
                                                      response_data=response_data), "utf-8"))
            if debugger_logs:
                print('sent the response from post request handler')
        elif route_pattern_for_existing_orders_request.match(data.splitlines()[0]):  # Handles the GET request for orders
            if debugger_logs:
                print('Received get request on route /orders')
            order_number = data.splitlines()[0].split(' ')[1].split('/')[-1]
            # Communicating with Order Service
            can_be_processed = False
            t_s = socket.socket()
            try:
                t_s.connect((OrderHost, order_service_port))
                can_be_processed = True
            except socket_error as e:  # Failed to connect to the leader
                print('Exception while Connecting to the leader ', e)
                new_order_service_port = perform_leader_election_of_order_services(available_order_service_ports)
                if new_order_service_port is None:
                    if debugger_logs:
                        print('FrontEnd Service Can\'t Process Order Requests as no Order Service is Up')
                else:
                    if debugger_logs:
                        print('The Front End Service will now send requests to {}'.format(new_order_service_port))
                    order_service_port = new_order_service_port
                    t_s.connect((OrderHost, order_service_port))
                    can_be_processed = True
            except Exception as e:  # Failed at processing in the Order Leader
                print('Exception while Processing in the order service ', e)
            if can_be_processed:
                t_s.send(bytes(json.dumps({"method_name": "query", "order_number": '{}'.format(order_number)}), 'utf-8'))
                response = eval(t_s.recv(1024).decode("utf-8"))  # response from Order Service
                t_s.close()
                flag, res_data = response[0], response[1]  # successful if flag=True, else failure
            else:
                flag, res_data = False, {"code": 500, "message": "could not get the order details right now due to Internal Server Issues"}

            payload = json.dumps(res_data)
            if flag:  # successful, adding status 200 and toy data to the output
                response_data = '{' + qry_success_response_data_format.format(payload=payload) + '}'
                c.send(bytes(
                    response_template.format(status_code=200,
                                             status_message="OK",
                                             content_length=len(payload) + L + L1,
                                             response_data=response_data), "utf-8"))
            else:  # failed to get the data, adding status 200 and error response to the output
                response_data = '{' + qry_error_response_data_format.format(payload=payload) + '}'
                c.send(bytes(
                    response_template.format(status_code=200,
                                             status_message="OK",
                                             content_length=len(payload) + L + L2,
                                             response_data=response_data), "utf-8"))
            if debugger_logs:
                print('sent the response from get request on orders')
        elif route_pattern_for_update_cache_request.match(data.splitlines()[0]):  # Handles the POST request
            if debugger_logs:
                print('Received post request on route /update_cache')
            req_bod = json.loads(data.splitlines()[-1])
            read_write_lock.acquire_write_lock()  # To maintain the state of the cache consistently
            for item in req_bod['items']:
                cached_data.catalog_data.pop(item, 'not_found')
            read_write_lock.release_write_lock()
            if debugger_logs:
                print('Updated the Cache for following items: {}'.format(req_bod['items']))
            if debugger_logs:
                print('sent the response update cache handler')
        else:
            # Handle for Invalid Requests
            if debugger_logs:
                print('Received an invalid request')
            payload = json.dumps({"message": "Invalid Request"})
            response_data = '{' + error_response_data_format.format(payload=payload) + '}'
            c.send(bytes(response_template.format(status_code=400,
                                                  status_message="Not Found",
                                                  content_length=len(payload) + L + L3,
                                                  response_data=response_data), "utf-8"))
            if debugger_logs:
                print('sent the response from Error Handler')
    c.close()


cached_data = CachedData()
read_write_lock = ReadWriteLock()

exe = ThreadPoolExecutor(max_workers=10)  # Thread Pool initializer

# dependent host services
# CatalogHost = os.getenv("CatalogHost", "catalog")
CatalogHost = os.getenv("CatalogHost", "127.0.0.1")
catalog_service_port = 9001

# start socket connection
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 8081))
s.listen(100)

# Master Worker Thread
while True:
    connection, client_addr = s.accept()
    try:
        exe.submit(request_processor, c=connection, addr=client_addr)
    except Exception as e:
        print('Couldn\'t process the request on front-end service for req_obj')
        connection.close()
