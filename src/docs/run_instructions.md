This document provides overview of how to run

### Move into the src folder

### To Run The Catalog Service

`python3 catalog/service.py`

### To Run The Order Services

`python3 order/service.py 8091 8091,8092,8093`

Here

- 8091 is the port of current order service

- 8091,8092,8093 is the list of order services that are expected to be running

Note:

- Variable Services can be run
- ../data/log_data folder is expected to be present

### To Run The FrontEnd Service

`python3 frontend/service.py 8091,8092,8093`

- 8091,8092,8093 is the list of order service ports that are expected to be running

(Always runs in 8081)

### To Run The Client

python3 client/client.py [arg_1] [arg_2] [arg_3] [arg_4] [arg_5]

- arg_1 is the number of clients
- arg_2 is the number of requests each client make
- arg_3 is the maximum quantity in a buy request
- arg_4 is the probability of making a probability
- arg_5 is the host parameter

`python3 client/run.py 5 100 5 0.75 ec2-54-167-21-148.compute-1.amazonaws.com`

host parameter:

- For running in aws, value is aws publicDNS.
- If host is not provided, default value is localhost.

### To Run The Test Suite

`python3 test/test_script.py {host}`

### To Run The Unit Test Cases

`python3 test/unit_suite_cases.py {host}`

## NOTE

#### LOGS

`Currently The Debugger mode is turned on in all services, This will flush Logs`

`To Disable this set debugger_logs=False In all services`

#### Cache

`Currently The Cache is enabled, to test results without Cache set CACHE_NOT_AVAILABLE=True in frontend/service.py`