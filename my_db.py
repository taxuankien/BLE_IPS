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
dis_ref = np.sqrt(0.545**2 + 0.19 **2)

connection_string = "mysql+mysqlconnector://root:123@127.0.0.1:3306/db"
engine = sqlalchemy.create_engine(connection_string)
query = "select * from rawrssi where timestamp >= '2024-05-24 10:00:00' and x < 10 and y <10"


df = pd.read_sql(query, engine)

training_df = df[((np.round(df['x'], 3) - 0.55 ) == np.floor((df['x'] - 0.55 )))  & ((np.round(df['y'] , 2) - 0.19 )== np.floor((df['y'] - 0.19 ))) | ((df['x'] > 2.5) & (df['x']<2.6))]
# test_df = df[((np.round(df['x'], 3) - 0.545 ) != np.floor((df['x'] - 0.545 )))  | ((np.round(df['y'] , 2) - 0.19 )!= np.floor((df['y'] - 0.19 ))) & (df['x'] != 1.545)]
# print(np.round((df['x'] - 0.545 )))
print(training_df)
temp = training_df[['x', 'y', 'Anchor','RSSI']]
print(temp.info())
temp = temp.groupby(['x','y','Anchor'])['RSSI'].mean().reset_index()
# test = test_df.groupby(['x', 'y', 'Anchor'])['RSSI'].ewm(alpha=0.5).mean().reset_index()

offline_np = temp.to_numpy()
# testing_np = test.to_numpy()
# print(offline_df)
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

# for i in range(int(testing_np[:,0]/num_anchor)):
#     test_db[i, 0:2] = testing_np[4*i, :2]
#     for y in range(num_anchor):
#         test_db[i:, 4+2*y:6+2*y] = testing_np[4*i+y,2:]

# print(fingerprint)

fingerprint_df = pd.DataFrame(fingerprint, columns= ['x', 'y', 'x_WC', 'y_WC', 'Anchor0', 'RSSI0', 'Anchor1', 'RSSI1', 'Anchor2', 'RSSI2', 'Anchor3', 'RSSI3'])
fingerprint_df.columns.name = 'RP'

# testing_df = pd.DataFrame(test_db, columns=['x', 'y', 'x_WC', 'y_WC', 'Anchor0', 'RSSI0', 'Anchor1', 'RSSI1', 'Anchor2', 'RSSI2', 'Anchor3', 'RSSI3'])


# APC
rssi_y = fingerprint_df[['RSSI0', 'RSSI1', 'RSSI2', 'RSSI3']]

af = AffinityPropagation(damping= 0.7, max_iter= 100, verbose= True).fit(rssi_y)
# km = KMeans(n_clusters=5, random_state=0, n_init= 'auto').fit(rssi_y)

label = af.labels_
exampler_indices = af.cluster_centers_indices_
# save cluster
cluster_center = np.zeros(len(label))
for i in range(5):
    cluster_center[np.where(label == i)] = exampler_indices[i]
fingerprint_df['RP_head'] = cluster_center
# 
# Plot clusters
pca = PCA(n_components=2)
coords = pca.fit_transform(rssi_y)
plt.figure()
sns.scatterplot(x = coords[:, 0], y = coords[:, 1], hue = label, palette=sns.color_palette("hls",5), legend= 'full')

# print(silhouette_score(rssi_y,labels=label, metric= 'euclidean'))
# print(coordinates)

# Weight Centroid 
file = open("pathloss_model.pkl", 'rb')
pathloss_model = pickle.load(file)
rssi_n_anchor = fingerprint_df[['RSSI0', 'RSSI1', 'RSSI2', 'RSSI3']].to_numpy()
# print(rssi_n_anchor)
dis_to_RPs = np.zeros((len(label), num_anchor))
for i in range(num_anchor):
    dis_to_RPs[:, i] = pathloss_model.predict(rssi_n_anchor[:,i].reshape(-1, 1))[:, 0]

dis_to_RPs = np.power(dis_to_RPs, 10)* dis_ref
# print(dis_to_RPs)
coords_WC = np.zeros((len(label), 2))
weight_dis = 1/(dis_to_RPs)** g
coords_WC = weight_dis @ anchor
# print(np.sum(weight_dis, axis= 1))
coords_WC = coords_WC/np.sum(weight_dis, axis= 1).reshape(-1,1)
coords_WC = np.round(coords_WC, 2)
# print(coords_WC)

# add WC to database
fingerprint_df[['x_WC', 'y_WC']] = coords_WC

fingerprint_df.to_csv("fingerprint_db.csv", index= False)
# print(fingerprint_df)
plt.show()

# xu ly du lieu kiem thu

