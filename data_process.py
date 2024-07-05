import socket
import pandas as pd
import asyncio
import datetime
import numpy as np
import pickle
from sklearn.linear_model import LinearRegression
import time

hostname = '127.0.0.1'
port = 8000
file = open("pathloss_model.pkl", 'rb')
pathloss_model = pickle.load(file)
ref_rssi = -57.835
alpha = 0.7

stored_file = open("position_history.txt", 'a')

fingerprint_db = pd.read_csv('fingerprint_db.csv')
dataframe = pd.DataFrame({'id':[], 'Anchor':[], 'RSSI':[]})

anchor = np.array([ [0,     5.84],
                    [5.95,  5.84],
                    [5.95,  0],
                    [0,     0]])
g = 0.7
num_anchor = 4
dis_ref = 1
loss_rssi = -100
        
def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: return str(i.split(':')[1].strip())

async def handle_client(client : socket.socket, queue : asyncio.Queue):
    loop = asyncio.get_running_loop()
    request = None
    print(client)
    while client:
        request = (await loop.sock_recv(client, 1024)).decode('utf8')
        if request:
            try:
                queue.put_nowait(request)
            except asyncio.QueueFull:
                print("QueueFull exception!")
            except ConnectionAbortedError:
                print("Done")
                break

async def data_storage(queue: asyncio.Queue):
    loop = asyncio.get_running_loop()
    global dataframe
    while True:
        data = await queue.get()
        data = data.split("\n")
        for i,item in enumerate(data):
            if len(item) > 20:
                arr = item.split(",")
                if(len(arr) == 3):
                    new_row = pd.DataFrame({'id': np.array([arr[1]]), 'Anchor': np.array([int(float(arr[0]))]), 'RSSI':np.array([float(arr[2])])})
                    dataframe = pd.concat([dataframe, new_row], ignore_index=True)

async def data_process():
    global dataframe
    global fingerprint_db
    global stored_file

    while True:
        print("Waiting ...")
        await asyncio.sleep(20)
        time_tmp = time.time()
        current_datetime = datetime.datetime.now()
        if not dataframe.empty:
            data_copy = dataframe[['id','Anchor','RSSI']].copy(deep=True)
            # print(data_copy.info())
            data_copy.reset_index(drop=True, inplace=True)
            dataframe.drop(dataframe.index , inplace=True)
            data_copy = data_copy.groupby(by = ['id',"Anchor"], as_index=False)["RSSI"].ewm(alpha= alpha, adjust= False).mean().reset_index()
            data_copy = data_copy.groupby(['id',"Anchor"]).tail(1).reset_index()
            print(data_copy.head())
            # tach du lieu id va rssi
            id_arr = data_copy[['id']].to_numpy(dtype= object)
            id_arr = np.unique(id_arr)                          #array luu id cua du lieu truc truyen
            num_id = id_arr.size
            
            data_np = data_copy[['Anchor', 'RSSI']].to_numpy()
            rssi_np = np.ones((num_anchor * num_id, 1)) * -100  #chuyen du lieu sang numpy va them cac rssi thieu
            idx = 0
            for i in range(0, num_id):
                for j in range(num_anchor):
                    if(idx == data_np.shape[0]):
                        break
                    if(j == data_np[idx, 0]):
                        rssi_np[4 * i + j, 0] = data_np[idx, 1]
                        idx += 1 
            if rssi_np.size >=4 :
                rssi_np = rssi_np.reshape((num_id,num_anchor))      #array luu rssi cua du lieu truc tuyen
                
                #uoc luong WC
                dis_from_Anchors = np.zeros((num_id,num_anchor))
                for i in range(num_anchor):
                    dis_from_Anchors[:,i] = pathloss_model.predict(ref_rssi - rssi_np[:,i].reshape(-1,1))[:,0]
                # print(dis_from_Anchors.shape)
                dis_from_Anchors = np.power(10, dis_from_Anchors) * dis_ref
                weighted_dis = (1/dis_from_Anchors) ** g
                sum_wdis = np.sum(weighted_dis, axis = 1)
                test_WC_coords = weighted_dis @ anchor / sum_wdis[:, np.newaxis]  #toa do trong tam cua cac diem test theo id
                # print("test WC coords: " + str(test_WC_coords))
                # so sanh WC cua cac dau cum de lua chon cum
                WC_center_np = fingerprint_db[['RP_head']].to_numpy()
                WC_center_indices = np.unique(WC_center_np)
                WC_center = fingerprint_db.iloc[WC_center_indices, [2, 3]].to_numpy()
                # print("RP indices: " + str(WC_center_indices)+" \nWC of RP head: "+ str(WC_center))

                # so sanh khoang cach den cac wc cua tam cum
                coord = []
                
                for i in range (num_id):
                    dis_RP_head = np.linalg.norm(WC_center - test_WC_coords[i, :], axis = 1)
                    idx = np.argsort(dis_RP_head)[0]
                    # 
                    selected_head_idx = WC_center_indices[idx]
                    # print("Cluster selected: "+ str(selected_head_idx))
                    # lay thong tin cac RP trong cum
                    selected_RP = fingerprint_db[fingerprint_db['RP_head'] == selected_head_idx]
                    # uoc luong toa do theo hai fingerprint
                    truth_RP_coords = selected_RP[['x', 'y']].to_numpy()
                    WC_RP_coords = selected_RP[['x_WC', 'y_WC']].to_numpy()
                    RP_rssi = selected_RP[['RSSI0', 'RSSI1', 'RSSI2', 'RSSI3']].to_numpy()
                    WC_dis = np.linalg.norm(WC_RP_coords - test_WC_coords[i, :], axis= 1)

                    RP_calculation_idx = np.argsort(WC_dis)[:3]
                    RP_nearest_idx = RP_calculation_idx[0]
                    # toa do theo WC
                    weight_WC = 1/WC_dis
                    WC_coord = weight_WC[RP_calculation_idx] @ truth_RP_coords[RP_calculation_idx, :] /sum(weight_WC[RP_calculation_idx])
                    # print(WC_coord)
                    # toa do theo RSSI
                    rssi_dis = np.linalg.norm(RP_rssi - rssi_np[i, :], axis= 1)
                    weight_rssi = 1/rssi_dis
                    rssi_coord = weight_rssi[RP_calculation_idx] @ truth_RP_coords[RP_calculation_idx, :]/sum(weight_rssi[RP_calculation_idx])
                    # print(rssi_coord)
                    # trung binh co trong so 2 toa do
                    rssi_test_decreasing = np.argsort(rssi_np[0,:])
                    rssi_RP_decreasing = np.argsort(RP_rssi[RP_nearest_idx, :])
                    # print(rssi_test_decreasing)
                    # print(rssi_RP_decreasing)
                    a = 4 - np.count_nonzero(rssi_test_decreasing - rssi_RP_decreasing)

                    coord.append( a/4 * WC_coord + (1- a/4)*rssi_coord)
                for i in range (len(coord)):
                    result = current_datetime.strftime("%d/%m/%Y %H:%M:%S") + ": " + str(id_arr[i])+ " at "+ str(coord[i]) + '\n'
                    stored_file.write(result)
                    stored_file.flush()
                    print(result)
                print(time.time() - time_tmp)
                           


async def run_server():
    # host = wlan_ip()
    global hostname
    
    queue = asyncio.Queue(0)
    while True:
        host = hostname
        if(host != None):
            print(host)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((host, port))
            server.listen(5)
            server.setblocking(False)
            loop = asyncio.get_running_loop()
            loop.create_task(data_process())
            while True:
                client,_ = await loop.sock_accept(server)
                loop.create_task(handle_client(client,queue))
                loop.create_task(data_storage(queue))
                print(client)

asyncio.run(run_server())


