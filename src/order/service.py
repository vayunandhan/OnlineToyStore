import json
import os
import socket
import sys
import time
import csv

import threading

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(sys.path[0], '..'))

from ReadWriteLock import ReadWriteLock

debugger_logs = True


# persists the log data
def update_the_log_file(new_log_data, file_path):
    try:
        with open(file_path, 'a') as file:
            writer = csv.writer(file)
            writer.writerows(new_log_data)
    except Exception as e:
        print('Could not Update The Log File', e)
        sys.exit()


# recover the older order number on service boot
def fetch_the_last_order_number_from_log_file(file_path):
    try:
        data = open(file_path, 'r').read()
    except FileNotFoundError as e:
        print('No Log File Present')
        return ['0,None,None']
    return data.strip('\n').split('\n')


class Orders:
    def __init__(self, id):
        self.log_file = '../data/log_data/log{}.csv'.format(id)  # relative path of the logs disk file
        self.current_order_state = fetch_the_last_order_number_from_log_file(self.log_file)  # current order number
        self.current_leader_order = None


orders = Orders(int(sys.argv[1]))


def get_order_index(order_num):
    for index in range(len(orders.current_order_state)):
        if int(orders.current_order_state[index].split(',')[0]) == order_num:
            return index
    return len(orders.current_order_state)


def send_the_missed_orders(current_order_num):
    index = get_order_index(current_order_num)
    return orders.current_order_state[index + 1:]


def update_the_missed_orders(port_used, all_order_services_ports):
    for order_services_port in all_order_services_ports:
        if port_used != order_services_port:
            try:
                t_s = socket.socket()
                t_s.connect((order_host_address, order_services_port))
                t_s.send(bytes(
                    json.dumps({"method_name": "fetch_the_latest_order_log", "order_num": '{}'.format(int(orders.current_order_state[-1].split(',')[0]))}),
                    'utf-8'))
                log_data = []
                while True:
                    response = t_s.recv(1024)  # response from the Active Order Service
                    if not response:
                        break
                    log_data.append(response)
                t_s.close()
                missed_logs = json.loads(b''.join(log_data).decode("utf-8"))
                orders.current_order_state.extend(missed_logs['log_data'])
                missed_logs = [log.split(',') for log in missed_logs['log_data']]
                for i in range(len(missed_logs)):
                    missed_logs[i][0], missed_logs[i][1], missed_logs[i][2] = int(missed_logs[i][0]), missed_logs[i][1], int(missed_logs[i][2])
                update_the_log_file(missed_logs, orders.log_file)
                print('Updated The Order Logs From {}'.format(order_services_port))
                return
            except Exception as e:
                print('Exception While Connecting to the order server: {}'.format(order_services_port))
                continue
    print('No Order Services are Up Yet')


def order_service(c, req_obj):
    if debugger_logs:
        print('Received an order request with req_obj: {}'.format(req_obj))
    if req_obj['method_name'] == 'health_check':  # handle for health-check
        c.send(bytes('Success', 'utf-8'))
        if debugger_logs:
            print('Sent the response for health_check from order service')
    elif req_obj['method_name'] == 'update_leader':  # handle to store leader
        orders.current_leader_order = int(req_obj['leader_id'])
        print('Updated the leader to: {}'.format(orders.current_leader_order))
        c.send(bytes('Success', 'utf-8'))
        if debugger_logs:
            print('Sent the response for update_leader from order service')
    elif req_obj['method_name'] == 'update_order_log':  # handle to update the log data sent from the leader
        log_record = req_obj['log_data']
        read_write_lock.acquire_write_lock()
        order_count, name, quantity = str(log_record).split(',')
        update_the_log_file([[int(order_count), name, int(quantity)]], orders.log_file)
        orders.current_order_state.append(log_record)
        read_write_lock.release_write_lock()
        c.send(bytes('Success', 'utf-8'))
        if debugger_logs:
            print('Sent the response for update_order_log from order service')
    elif req_obj['method_name'] == 'fetch_the_latest_order_log':  # handle to send the missed log data to the follower
        read_write_lock.acquire_write_lock()
        missed_logs = send_the_missed_orders(int(req_obj['order_num']))
        read_write_lock.release_write_lock()
        response = bytes(json.dumps({"log_data": missed_logs}), 'utf-8')
        chunks = [response[i:i + 1024] for i in range(0, len(response), 1024)]
        for chunk in chunks:
            c.send(chunk)
        if debugger_logs:
            print('Sent the response for fetch_the_latest_order_log from order service')
    elif req_obj['method_name'] == 'query':  # handle for query
        sent = False
        read_write_lock.acquire_read_lock()
        for row in orders.current_order_state:
            order_num, name, quantity = row.split(',')
            if int(order_num) == int(req_obj['order_number']):
                read_write_lock.release_read_lock()
                res = True, {"number": int(order_num), "name": name, "quantity": float(quantity)}
                c.send(bytes(str(res), 'utf-8'))
                sent = True
                break
        read_write_lock.release_read_lock()
        if not sent:
            res = False, {"code": 404, "message": "order_number: {} not found".format(req_obj['order_number'])}
            c.send(bytes(str(res), 'utf-8'))
        if debugger_logs:
            print('Sent the response for query from order service')
    else:  # handle for order
        req_obj = req_obj['data']
        if int(req_obj['quantity']) < 0:  # handle for invalid quantity
            res = False, {"code": 404, "message": "Invalid Quantity"}
            c.send(bytes(str(res), 'utf-8'))
        else:
            # communicates with the Catalog Service
            t_s = socket.socket()
            t_s.connect((CatalogHost, catalog_service_port))
            t_s.send(bytes(json.dumps({"method_name": "decrement", "order": '{}'.format(req_obj)}), 'utf-8'))
            response = t_s.recv(1024).decode("utf-8")  # response from the Catalog Service
            response = eval(response)
            t_s.close()
            if response:  # order placed
                read_write_lock.acquire_write_lock()
                current_order_count = int(orders.current_order_state[-1].split(',')[0])
                current_order_count += 1
                res = True, {"order_number": current_order_count}
                update_the_log_file([[current_order_count, req_obj['name'], req_obj['quantity']]], orders.log_file)
                orders.current_order_state.append(','.join([str(current_order_count), str(req_obj['name']), str(req_obj['quantity'])]))
                for follower_order_node in all_order_services_ports:
                    if follower_order_node != port_used:
                        try:
                            t_s = socket.socket()
                            t_s.connect((order_host_address, follower_order_node))
                            t_s.send(bytes(json.dumps(
                                {"method_name": "update_order_log",
                                 "log_data": '{}'.format(','.join([str(current_order_count), req_obj['name'], str(req_obj['quantity'])]))}),
                                'utf-8'))
                            response = t_s.recv(1024).decode("utf-8")  # response from the Follower Order Service
                            t_s.close()
                            if debugger_logs:
                                print(response)
                        except Exception as e:
                            print('Exception Occurred while sending the log data to {}'.format(follower_order_node), e)
                read_write_lock.release_write_lock()
                c.send(bytes(str(res), 'utf-8'))
            else:  # order not placed
                res = False, {"code": 404, "message": "could not place the order"}
                c.send(bytes(str(res), 'utf-8'))
        if debugger_logs:
            print('Sent the response for order from order service')
    c.close()


read_write_lock = ReadWriteLock()

N = 10  # Number of Threads
exe = ThreadPoolExecutor(max_workers=N)  # Thread Pool Initiator

# dependent host services
# CatalogHost = os.getenv("CatalogHost", "catalog")
CatalogHost = os.getenv("CatalogHost", "127.0.0.1")
catalog_service_port = 9001

port_used = int(sys.argv[1])
all_order_services_ports = [int(i) for i in sys.argv[2].split(',')]  # Arguments

# start socket connection
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
order_host_address = '0.0.0.0'
s.bind((order_host_address, port_used))
s.listen(100)

# Update the missed orders
update_the_missed_orders(port_used, all_order_services_ports)  # No Synchronization Required

# Master Worker Thread
while True:
    connection, client_address = s.accept()
    if debugger_logs:
        print('Connection established from {}'.format(client_address))
    req_obj = connection.recv(1024).decode("utf-8")
    req_obj = req_obj.replace('\'', '"')
    try:
        exe.submit(order_service, c=connection, req_obj=json.loads(req_obj))
    except Exception as e:
        print('Couldn\'t process the request on order service for req_obj: {}'.format(req_obj))
        connection.close()
