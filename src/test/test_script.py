import socket
import json
import sys

host = sys.argv[1]
port = 8081


# catalog query for valid item
def query_with_valid_item():
    print('Query catalog for valid item: Tux')
    s = socket.socket()
    s.connect((host, port))
    s.send(bytes('GET /products/Tux HTTP/1.1', 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response for valid item:', res_json)
    s.close()


# catalog query for invalid item
def query_with_invalid_item():
    print('Query catalog for invalid item')
    s = socket.socket()
    s.connect((host, port))
    s.send(bytes('GET /products/Random HTTP/1.1', 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response:', res_json)
    s.close()


# order request for invalid item
def order1():
    print('Order invalid item')
    s = socket.socket()
    s.connect((host, port))
    req_body = {
        "name": "Random",
        "quantity": 1
    }
    s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response:', res_json)
    s.close()


# order request for valid item and proper quantity
def order2():
    print('Order valid item(Tux) with less than or equal to quantity')
    s = socket.socket()
    s.connect((host, port))
    req_body = {
        "name": "Tux",
        "quantity": 1
    }
    s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response:', res_json)
    s.close()


# order request for valid item and quantity = 10000000
def order3():
    print('Order valid item(Tux) with greater quantity')
    s = socket.socket()
    s.connect((host, port))
    req_body = {
        "name": "Tux",
        "quantity": 100000
    }
    s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response for invalid item:', res_json)
    s.close()


# order request for valid item and quantity = -1
def order4():
    print('Order valid item(Tux) with lower than zero')
    s = socket.socket()
    s.connect((host, port))
    req_body = {
        "name": "Tux",
        "quantity": -1
    }
    s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response for invalid item:', res_json)
    s.close()


# get order details for valid_item
def get_order_details_with_valid_id():
    print('Get Order details for valid order_id')
    s = socket.socket()
    s.connect((host, port))
    s.send(bytes('GET /orders/1 HTTP/1.1', 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response for order details for valid order id:', res_json)
    s.close()


# get order details for invalid order id
def get_order_details_with_invalid_id():
    print('Get Order details for invalid order_id')
    s = socket.socket()
    s.connect((host, port))
    s.send(bytes('GET /orders/-1 HTTP/1.1', 'utf-8'))
    res = s.recv(1024).decode("utf-8")
    arr = res.split('\n')
    arr[-1] = arr[-1].replace('\'', '"')
    res_json = json.loads(arr[-1])
    print('Response for order details for invalid order id:', res_json)
    s.close()


if __name__ == "__main__":
    query_with_invalid_item()
    query_with_valid_item()
    order1()
    order2()
    order3()
    order4()
    get_order_details_with_valid_id()
    get_order_details_with_invalid_id()
