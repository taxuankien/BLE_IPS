import numpy as np
import pandas as pd
import sqlalchemy 
from sklearn.linear_model import LinearRegression
from sklearn.cluster import AffinityPropagation
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
import pickle

anchor = np.array([ [0,     5.84],
                    [5.95,  5.84],
                    [5.95,  0],
                    [0,     0]])
g = 0.7
num_anchor = 4
dis_ref = 1
damping_factor = 0.6
ref_rssi = -57.835

connection_string = "mysql+mysqlconnector://root:123@127.0.0.1:3306/db"
engine = sqlalchemy.create_engine(connection_string)
query = "select * from rawrssi where timestamp >= '2024-05-17 10:00:00' and timestamp < '2024-06-16 10:00:00' and x < 10 and y <10 and id = '00000000000000000000000000000001'"


df = pd.read_sql(query, engine)

training_df = df[(df['x'] % 1 < 0.6) & (df['x'] % 1 > 0.54) & (df['y'] % 1 < 0.2) & (df['y'] % 1 > 0.18)]
training_df['x'] = np.ceil(training_df['x']) - 0.45

training_df['date'] = training_df['timestamp'].dt.date

training_df = training_df.groupby(['x','y', 'Anchor', 'date']).sample(100, replace= True).reset_index()

temp = training_df[['x', 'y', 'Anchor','RSSI']]
temp = temp.groupby(['x','y','Anchor'])['RSSI'].mean().reset_index()
# test = test_df.groupby(['x', 'y', 'Anchor'])['RSSI'].ewm(alpha=0.5).mean().reset_index()

offline_np = temp.to_numpy()
coordinates = np.unique(offline_np[:, 0:2], axis = 0)
# testing_coords = np.unique(testing_np[:, 0:2], axis = 0)

rssi_db = np.array(offline_np[:, 2:])
print(offline_np[:, 0].size)
length = int(offline_np[:, 0].size/num_anchor)
fingerprint = np.zeros((length, 12))
# test_db = np.zeros((int(testing_np[:,0]/num_anchor), 12))
for i in range(length):
    fingerprint[i, 0:2] = offline_np[4*i, :2]
    # test_db[i, 0:2] = testing_np[4*i, :2]
    for y in range(num_anchor):
        fingerprint[i:, 4+2*y:6+2*y] = offline_np[4*i+y,2:]
        # test_db[i:, 4+2*y:6+2*y] = testing_np[4*i+y,2:]


fingerprint_df = pd.DataFrame(fingerprint, columns= ['x', 'y', 'x_WC', 'y_WC', 'Anchor0', 'RSSI0', 'Anchor1', 'RSSI1', 'Anchor2', 'RSSI2', 'Anchor3', 'RSSI3'])
fingerprint_df.columns.name = 'RP'

# testing_df = pd.DataFrame(test_db, columns=['x', 'y', 'x_WC', 'y_WC', 'Anchor0', 'RSSI0', 'Anchor1', 'RSSI1', 'Anchor2', 'RSSI2', 'Anchor3', 'RSSI3'])


# APC
rssi_y = fingerprint_df[['RSSI0', 'RSSI1', 'RSSI2', 'RSSI3']]

af = AffinityPropagation(damping= damping_factor, max_iter= 100, verbose= True).fit(rssi_y)
# km = KMeans(n_clusters=5, random_state=0, n_init= 'auto').fit(rssi_y)

label = af.labels_
exampler_indices = af.cluster_centers_indices_
# save cluster
cluster_center = np.zeros(len(label))
for i in range(exampler_indices.size):
    cluster_center[np.where(label == i)] = exampler_indices[i]
fingerprint_df['RP_head'] = cluster_center
# 
# Plot clusters
coords = fingerprint_df[['x', 'y']].to_numpy()
plt.figure()
print("line 77: ", str(label))
print("line 78: ", str(exampler_indices))
sns.scatterplot(x = coords[:, 0], y = coords[:, 1], hue = label, palette=sns.color_palette("hls",exampler_indices.size), legend= 'full')

# print(silhouette_score(rssi_y,labels=label, metric= 'euclidean'))
# print(coordinates)

# Weight Centroid 
file = open("pathloss_model.pkl", 'rb')
pathloss_model = pickle.load(file)
print("coef of model: ", str(1/pathloss_model.coef_/10))
rssi_n_anchor = fingerprint_df[['RSSI0', 'RSSI1', 'RSSI2', 'RSSI3']].to_numpy()

dis_to_RPs = np.zeros((len(label), num_anchor))
for i in range(num_anchor):
    dis_to_RPs[:, i] = pathloss_model.predict(ref_rssi - rssi_n_anchor[:,i].reshape(-1, 1))[:, 0]

dis_to_RPs = np.power(10, dis_to_RPs)* dis_ref
coords_WC = np.zeros((len(label), 2))
weight_dis = 1/((dis_to_RPs)** g)
coords_WC = weight_dis @ anchor
coords_WC = coords_WC/np.sum(weight_dis, axis= 1).reshape(-1,1)
coords_WC = np.round(coords_WC, 2)
# print(dis_to_RPs)
# print(weight_dis)
# print(coords_WC)

# add WC to database
fingerprint_df[['x_WC', 'y_WC']] = coords_WC

fingerprint_df.to_csv("fingerprint_db.csv", index= False)
# print(fingerprint_df)
plt.show()

# xu ly du lieu kiem thu

