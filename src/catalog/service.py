import json
import os
import socket
import sys
import time
import threading
import csv
import inspect
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(sys.path[0], '..'))

from ReadWriteLock import ReadWriteLock

debugger_logs = True


# updates the Catalog CSV file on disk["database"] when order is successful
def update_the_catalog_file(current_data, file_path):
    lines = [['toy_name', 'price', 'quantity']]
    for toy in current_data:
        lines.append([str(toy), str(current_data[toy]['price']), str(current_data[toy]['quantity'])])
    with open(file_path, 'w') as file:
        writer = csv.writer(file)
        writer.writerows(lines)


# initializes the in_memory catalog data on service boot
def create_catalog_dictionary(file_path):
    try:
        content = open(file_path, 'r').read()
        if debugger_logs:
            print(os.getcwd())
    except FileNotFoundError as e:
        print('Could Not Read The Catalog File')
        return {}
    rows = content.strip('\n').split('\n')
    catalog = {}
    rows = rows[1:]
    for row in rows:
        name, price, quantity = row.split(',')
        price = float(price)
        quantity = 100  # Initial Value needs to be 100 when the service is up
        catalog[name] = {'price': price, 'quantity': quantity}
    return catalog


class Catalog:
    def __init__(self):
        self.content_file = '../data/catalog_data/catalog.csv'  # relative path of the disk file
        self.catalog = create_catalog_dictionary(self.content_file)  # in memory catalog data

    # fetches the given toy data
    def query_the_catalog(self, toy_name):
        if toy_name in self.catalog:  # found the toy in catalog
            return True, {"name": toy_name, "price": self.catalog[toy_name]['price'], "quantity": self.catalog[toy_name]['quantity']}
        else:  # not found
            return False, {"code": 404, "message": "product not found"}

    # updates the catalog[memory & disk] for each order
    def update_the_catalog(self, order_req):
        order_req = json.loads(order_req.replace('\'', '"'))
        if order_req['name'] in self.catalog and self.catalog[order_req['name']]['quantity'] - order_req['quantity'] >= 0:  # order can be placed
            self.catalog[order_req['name']]['quantity'] -= order_req['quantity']
            update_the_catalog_file(self.catalog, self.content_file)
            # Sending Update Request To FrontendService
            t_s = socket.socket()
            t_s.connect((FrontendServiceHost, frontend_service_port))
            req_body = {
                "items": [order_req['name']]
            }
            t_s.send(bytes('POST /update_cache HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))  # send order request
            t_s.close()  # Closing The Connection
            return True
        else:  # Can't place the order
            return False

    def restock_the_toys(self):
        restocked_items = []
        read_write_lock.acquire_write_lock()  # Prevents Others From Updating Catalog
        for toy in self.catalog:
            if self.catalog[toy]['quantity'] != 100:  # Fixed Value
                self.catalog[toy]['quantity'] = 100  # Fixed Value
                restocked_items.append(toy)
        update_the_catalog_file(self.catalog, self.content_file)
        read_write_lock.release_write_lock()
        # Sending Update Request To FrontendService
        try:
            t_s = socket.socket()
            t_s.connect((FrontendServiceHost, frontend_service_port))
            req_body = {
                "items": restocked_items
            }
            t_s.send(bytes('POST /update_cache HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))  # send update request
            t_s.close()  # Closing The Connection
        except Exception as e:
            print('Error Occurred While Connecting to the FrontEnd Service from Catalog Service', e)

    def get_catalog_data(self, toy_name):
        read_write_lock.acquire_read_lock()
        if toy_name in self.catalog:
            available = True
        else:
            available = False
        read_write_lock.release_read_lock()
        if available:
            return True, self.catalog[toy_name]
        else:
            return False, {}


class RestockTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
            if debugger_logs:
                print('Restocking Finished at: {}'.format(datetime.now()))
            if debugger_logs:
                print('Catalog Data: {}'.format(catalog.catalog))


catalog = Catalog()
read_write_lock = ReadWriteLock()


def catalog_req_service(c, req_obj):
    if debugger_logs:
        print('Received request: {} on catalog service'.format(req_obj))
    if req_obj['method_name'] == 'query':  # handle for query
        read_write_lock.acquire_read_lock()  # Synchronization
        res = catalog.query_the_catalog(req_obj['toy_name'])
        read_write_lock.release_read_lock()
        c.send(bytes(str(res), 'utf-8'))
    elif req_obj['method_name'] == 'decrement':  # handle for order
        read_write_lock.acquire_write_lock()  # Synchronization
        res = catalog.update_the_catalog(req_obj['order'])
        read_write_lock.release_write_lock()
        c.send(bytes(str(res), 'utf-8'))
    elif req_obj['method_name'] == 'get_catalog_data':
        c.send(bytes(str(catalog.get_catalog_data(req_obj["toy_name"])), 'utf-8'))
    else:  # invalid method
        c.send(bytes('Method name: {} is invalid'.format(req_obj['method_name']), 'utf-8'))
    if debugger_logs:
        print('Sent the response from catalog service')
    c.close()


restock_timer = RestockTimer(10, catalog.restock_the_toys)  # 10 is Fixed Value
restock_timer.start()  # Runs till server is terminated   #TODO

# dependent host services
# FrontendServiceHost = os.getenv("FrontendHost", "frontend")
FrontendServiceHost = os.getenv("FrontendHost", "127.0.0.1")
frontend_service_port = 8081

N = 10  # Number of Threads
exe = ThreadPoolExecutor(max_workers=N)  # Thread Pool Initiator

# start socket connection
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 9001))
s.listen(100)

# Master Worker Thread
while True:
    connection, client_address = s.accept()
    req_obj = connection.recv(1024).decode("utf-8")
    try:
        exe.submit(catalog_req_service, c=connection, req_obj=json.loads(req_obj))
    except Exception as e:
        print('Couldn\'t process the request on catalog service for req_obj: {}'.format(req_obj))
        connection.close()
