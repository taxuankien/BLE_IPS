
# Indoor Positioning System
The indoor positioning system using is a solution that allows the determination of the position of objects within indoor environments. This project aims to design and implement an indoor positioning system using BLE technology, applicable in environments such as offices.


## Project structure
The following is the file structure of the project:
```bash
BLE_IPS/
├── dataset/                # Contains datasets for training and evaluation
├── Docker/                 # Docker configurations to configure mysql for data collection
├── esp32_ble_esp01/        # Firmware and scripts for ESP32 and ESP01 devices
├── training/               # Training scripts to construct radio map
├── check_db.ipynb          # Jupyter notebook for database checking
├── data_process.py         # Script for data processing (main program)
├── pathloss_model.pkl      # Pre-trained path loss model (propagation model)
├── position_history.txt    # Text file storing position history
└── README.md 
```
## Deployment
### ESP32
Run the firmware in the `esp32_ble_esp01/` directory using ESP-IDFIDF
```esp-idf
    cd esp32_ble_esp01/
    idf.py build
    idf.py -p COMx flash monitor
```
Note: Change the COM port to match COMx accordingly.
### Training
Run the docker-compose file in the Docker directory to start MySQL for storing collected data.
```bash
  cd Docker 
  docker compose up -d
  cd ../training
```
Run the `socket_server.py` to receive data from the Anchors and input the actual coordinates of the reference point.
```bash
    python socket_server.py
```
Note: The `socket_client.py` is used to test the data transmission to the database and simulate received data.

Run the `my_db.py` program to build a database for data in MySQL.
```bash
    python my_db.py
```

### Online 
Run the `data_process.py` program to start the process of collecting and processing data in real-time.
```bash
    cd ..
    python data_process.py
```



## Results
The result obtained is displayed as follows:
```bash
#time  id  coordinate
05/07/2024 08:31:44: 00000000-0000-0000-0000-0000000001f3 at [3.1461538  2.55285382]

```



## Database
The database of the project after the training phase is saved in the `dataset/` directory.
```bash
dataset/
├──fingerprint_db.csv   #The fingerprint data collected
├──training_data.csv    #RSSI data is used to build the fingerprint.
├──pathloss.csv         #The RSSI data is used to build the signal propagation model.
└──testing_data.csv     #The data consists of test points.

```