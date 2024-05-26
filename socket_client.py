import socket
import numpy as np
import sqlalchemy
import pandas as pd
import time

connection = "mysql+mysqlconnector://root:123@127.0.0.1:3306/db"
port = 8080


def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: 
                return str(i.split(':')[1].strip())

engine  = sqlalchemy.create_engine(connection)
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and x < 1.05 and x > 1 and y < 3"
query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and x < 10 and y < 10"
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and x < 3.05 and x > 3"
# query = "select * from rawrssi where timestamp > '2024-05-15 17:00:00' and y < 1.7 and y > 1.6"


df = pd.read_sql(query, engine)
count_data = df.groupby('Anchor').size()


# df= pd.concat([df, pd.read_sql(query, engine)], ignore_index = True)


# df= pd.concat([df, pd.read_sql(query, engine)], ignore_index = True)
print(count_data)

data = df[['Anchor', 'id', 'RSSI']].to_numpy()
# print(data)
coords = df[['x', 'y']].to_numpy()

host = wlan_ip()           
client_socket = socket.socket()
client_socket.connect((host, port))

for i in range(data[:,0].size):
    print(coords[i,:], end = '')
    string =   str(data[i, 0]) +','+str(data[i, 1]) + ','+str(data[i, 2]) + '\n'
    client_socket.send(string.encode())
    print(string, end=',')
    time.sleep(60/800)
print(data[:,0].size)



