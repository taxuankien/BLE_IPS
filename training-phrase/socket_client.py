import socket
import numpy as np
import sqlalchemy
import pandas as pd
import time
import uuid

connection = "mysql+mysqlconnector://root:123@127.0.0.1:3306/db"
port = 8000


def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: 
                return str(i.split(':')[1].strip())

def integer_to_uuid_string(num):
    # Chuyển đổi số nguyên thành chuỗi UUID
    uuid_obj = uuid.UUID(int=num)
    return str(uuid_obj)

engine  = sqlalchemy.create_engine(connection)
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and x < 1.05 and x > 1 and y < 3"
# query = "select * from rawrssi where timestamp > '2024-05-27 10:00:00' and x < 10 and y < 10"
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and x < 3.05 and x > 3"
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and y < 1.7 and y > 1.6"


df = pd.read_csv("testing_data(raw).csv")
# df = pd.read_sql(query, engine)

count_data = df.groupby('Anchor').size()

# print(count_data)

data = df[['Anchor', 'RSSI']].to_numpy()
print(data)
coords = df[['x', 'y']].to_numpy()

host = "127.0.0.1"         
client_socket = socket.socket()
client_socket.connect((host, port))
k = 0
n = int(input())
for i in range(4*k, n+4*k):
    # print(coords[i,:], end = '')
    tmp = integer_to_uuid_string(i)
    
    string =  str(int(data[i, 0])) +',' +tmp+ ','+str(data[i, 1]) + '\n'

    client_socket.send(string.encode())
    print(string, end='')
    time.sleep(0.01)
# print(data[:,0].size)



