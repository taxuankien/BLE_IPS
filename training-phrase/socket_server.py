import asyncio, socket
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
import time
import numpy as np
import datetime

def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: return str(i.split(':')[1].strip())

connection_string = "mysql+mysqlconnector://root:123@127.0.0.1:3306/db"

HOST = "192.168.137.1"
PORT =  8000
print(HOST)
x = float(input("x:"))
y = float(input("y:"))

class Base(DeclarativeBase):
    pass

class RawRssi(Base):
    __tablename__ =  "rawrssi"

    sq: Mapped[int] = mapped_column(sqlalchemy.INTEGER, primary_key= True)
    timestamp: Mapped[sqlalchemy.TIMESTAMP] = mapped_column(sqlalchemy.TIMESTAMP)
    id: Mapped[str] = mapped_column(sqlalchemy.VARCHAR(32))
    x: Mapped[float] = mapped_column(sqlalchemy.FLOAT(2,2))
    y: Mapped[float] = mapped_column(sqlalchemy.FLOAT(2,2))
    Anchor: Mapped[int] = mapped_column(sqlalchemy.INTEGER)
    RSSI: Mapped[int] = mapped_column(sqlalchemy.INTEGER)

    def __repr__(self) -> str:
        return f"Raw RSSI: id {self.id}, (x,y) = ({self.x}, {self.y}), rssi = ({self.Anchor}, {self.RSSI})"
    
    def decompose(data: str, x, y):
        arr = data.split(",")
        # tim = time.time()
        # print("timestamp: " +  str(float(tim)))
        return RawRssi(
                    timestamp = datetime.datetime.now(),
                    id = arr[1],
                    Anchor = int(arr[0]),
                    RSSI = int(arr[2]),
                    x = x,
                    y = y
        )

async def handle_client(client : socket.socket, queue : asyncio.Queue):
    loop = asyncio.get_running_loop()
    request = None
    count = 0
    while client:
        request = (await loop.sock_recv(client, 1024)).decode('utf8')
        if request:
            try:
                queue.put_nowait(request)
                count += 1
            except asyncio.QueueFull:
                print("QueueFull exception!")
            except ConnectionAbortedError:
                print("Done")
                break
        if count < 200:
            print(count, end= ' ')

async def handle_database( queue : asyncio.Queue, session: Session):
    loop = asyncio.get_running_loop()
    
    while True:
        data = await queue.get()
        data = data.split("\n")
        # print(data)
        for i,item in enumerate(data):
            # print(item)
            if len(item)>20:
                
                unit = RawRssi.decompose(item, x, y)
                print(item)
                session.add_all([unit])
                session.commit()

async def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    server.setblocking(False)
    queue = asyncio.Queue(0)
    
    engine = sqlalchemy.create_engine(connection_string)
    conn = engine.connect()
    if not sqlalchemy.inspect(engine).has_table("rawrssi") :
        Base.metadata.create_all(conn)
    else:
        print("rawrssi table existed")
    session = Session(engine)

    loop = asyncio.get_event_loop()
    while True:
        client, _ = await loop.sock_accept(server)
        loop.create_task(handle_client(client, queue))
        loop.create_task(handle_database(queue, session))
        print(client)

asyncio.run(run_server())