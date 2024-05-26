#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "esp_bt.h"
#include "esp_gap_ble_api.h"
#include "esp_gattc_api.h"
#include "esp_gatt_defs.h"
#include "esp_bt_main.h"
#include "esp_bt_defs.h"
#include "esp_ibeacon_api.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_common_api.h"

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"

#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "nvs_flash.h"

#define Anchor  (0)
static const char* TAG = "BEACON";
esp_ble_ibeacon_t* ibeacon_data;
QueueHandle_t beacon_queue;

#define ENDIAN_CHANGE_U16(x) ((((x)&0xFF00)>>8) + (((x)&0xFF)<<8))
#define SSID    "cien"
#define PWD     "abcde123"
#define HOST    "192.168.137.1"
#define PORT    (8000)

#define TXD_PIN (GPIO_NUM_5)
#define RXD_PIN (GPIO_NUM_4)
#define BUF_SIZE (1024)
#define PATTERN_CHR_NUM (1)

#define WIFI_BIT (1 << 0)
#define TCP_BIT (1 << 1)
#define SEND_BIT (1 << 2)

static QueueHandle_t uart1_queue;
// static EventBits_t uxBits;
static EventGroupHandle_t eventHandler;

// char cmd[50];
char data[512];

common_beacon_data_t beacon_data = {
    .rssi = 0
};

esp_ble_ibeacon_head_t ibeacon_common_head = {
    .length = 0x1A,
    .type = 0xFF,
    .company_id = 0x004C,
    .beacon_type = 0x1502
};

static esp_ble_scan_params_t ble_scan_params = {
    .scan_type              = BLE_SCAN_TYPE_PASSIVE,
    .own_addr_type          = BLE_ADDR_TYPE_PUBLIC,
    .scan_filter_policy     =  BLE_SCAN_FILTER_ALLOW_ALL,
    .scan_interval          = 0x20,
    .scan_window            = 0x18,
    .scan_duplicate         = BLE_SCAN_DUPLICATE_DISABLE
};

void convert_uint8_to_string(uint8_t* array, uint8_t length, char *str){

    for(int i = 0; i< length; i++){
        sprintf(str + 2*i, "%02X", *(array + i) & 0xff);
    }
    *(str + 2 * length) = '\0';
}

uint8_t is_beacon_packet(uint8_t *adv_data, uint8_t adv_data_len, uint8_t pos){
    uint8_t type = 0;
    if(!memcmp(adv_data+pos, (uint8_t*)&ibeacon_common_head, sizeof(ibeacon_common_head))){
        type = 1;
    }
    
    return type;
};

static void esp_gap_cb(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param){
    esp_err_t err;

    switch (event)
    {
    case ESP_GAP_BLE_SCAN_PARAM_SET_COMPLETE_EVT:
        uint32_t duration = 0;
        esp_ble_gap_start_scanning(duration);
        break;
    case ESP_GAP_BLE_SCAN_START_COMPLETE_EVT:
        if ((err = param->scan_start_cmpl.status) != ESP_BT_STATUS_SUCCESS) {
            ESP_LOGE(TAG, "Scan start failed: %s", esp_err_to_name(err));
        }
        else {
            ESP_LOGI(TAG,"Start scanning...");
            }
        break;
    case ESP_GAP_BLE_SCAN_RESULT_EVT:
        esp_ble_gap_cb_param_t *scan_result = (esp_ble_gap_cb_param_t *)param;
        
        switch(scan_result->scan_rst.search_evt){
        case ESP_GAP_SEARCH_INQ_RES_EVT:
            uint8_t pos = 0;
            // char id_string[32] = "";
            BaseType_t xHigherPriorityTaskWoken;
            if(scan_result->scan_rst.adv_data_len >= 20){
    
                if(scan_result->scan_rst.ble_adv[0] == 0x02){ 
                    pos = scan_result->scan_rst.ble_adv[0] + 1;
                }
                // uint8_t type = is_beacon_packet(scan_result->scan_rst.ble_adv, scan_result->scan_rst.adv_data_len, pos);
                if(is_beacon_packet(scan_result->scan_rst.ble_adv, scan_result->scan_rst.adv_data_len, pos)){
                    ibeacon_data = esp_ble_ibeacon_packet_decompose(scan_result->scan_rst.ble_adv, pos);
                    ESP_LOGI(TAG, "----------iBeacon Found----------");

                    beacon_data.major = ENDIAN_CHANGE_U16(ibeacon_data->ibeacon_vendor.major);
                    beacon_data.minor = ENDIAN_CHANGE_U16(ibeacon_data->ibeacon_vendor.minor);
                    beacon_data.rssi = scan_result->scan_rst.rssi;
                    beacon_data.tx_power = ibeacon_data->ibeacon_vendor.measured_power;
                    beacon_data.anchor = 1;
                    
                    // beacon_data.type = 1;
                    memcpy(beacon_data.uuid, ibeacon_data->ibeacon_vendor.proximity_uuid, ESP_UUID_LEN_128);
                    beacon_data.rssi = scan_result->scan_rst.rssi;
                    memcpy(beacon_data.add, scan_result->scan_rst.bda, ESP_BD_ADDR_LEN);
                    // convert_uint8_to_string((uint8_t*)beacon_data.uuid, ESP_UUID_LEN_128, id_string);
                    // sprintf(str, "%d,%s,%d",anchor ,id_string, beacon_data.rssi);
                    xHigherPriorityTaskWoken = pdFALSE;
                    xQueueSendFromISR(beacon_queue, (void *)&beacon_data, xHigherPriorityTaskWoken);
                    if( xHigherPriorityTaskWoken )
                    {
                        // portYIELD_FROM_ISR();
                        portYIELD_FROM_ISR();
                    }
                }
            }
            break;
        default:
            break;
        break;
        }
    case ESP_GAP_BLE_SCAN_STOP_COMPLETE_EVT:
        // ESP_LOGI(TAG, "Stop Scanning");
        break;
    default:
        break;
    }
}

void ble_beacon_appRegister(void){
    esp_err_t   status;
    ESP_LOGI(TAG, "register callback");

    if((status = esp_ble_gap_register_callback(esp_gap_cb)) != ESP_OK){
        ESP_LOGE(TAG,"gap register error: %s", esp_err_to_name(status));
        return;
    }
}
void uart_rx_task(void *arg)
{
    uart_event_t event;
    size_t buffered_size;
    uint8_t* dtmp;
    char rx_data[100];
    while(1){
        
        dtmp = (uint8_t*)malloc(BUF_SIZE);
        if(xQueueReceive(uart1_queue, (void*)&event, (TickType_t)portMAX_DELAY)){
            bzero(dtmp, BUF_SIZE);
            // ESP_LOGI(TAG, "uart[%d] event:", UART_NUM_1);
            switch (event.type){
                // case UART_DATA:
                    
                //     uart_read_bytes(UART_NUM_1, rx_data, 3, 100/ portTICK_PERIOD_MS);
                //     ESP_LOGI(TAG, "%s", rx_data);
                //     break;
                case UART_FIFO_OVF:
                    ESP_LOGI(TAG, "hw fifo overflow");
                    // If fifo overflow happened, you should consider adding flow control for your application.
                    // The ISR has already reset the rx FIFO,
                    // As an example, we directly flush the rx buffer here in order to read more data.
                    uart_flush_input(UART_NUM_1);
                    xQueueReset(uart1_queue);
                    break;
                case UART_BUFFER_FULL:
                    ESP_LOGI(TAG, "ring buffer full");
                    // If buffer full happened, you should consider increasing your buffer size
                    // As an example, we directly flush the rx buffer here in order to read more data.
                    uart_flush_input(UART_NUM_1);
                    xQueueReset(uart1_queue);
                    break;
                //Event of UART RX break detected
                case UART_BREAK:
                    ESP_LOGI(TAG, "uart rx break");
                    break;
                //Event of UART parity check error
                case UART_PARITY_ERR:
                    ESP_LOGI(TAG, "uart parity error");
                    break;
                //Event of UART frame error
                case UART_FRAME_ERR:
                    ESP_LOGI(TAG, "uart frame error");
                    break;
                case UART_PATTERN_DET:
                    char *pchar = NULL;
                    uart_get_buffered_data_len(UART_NUM_1, &buffered_size);
                    int pos = uart_pattern_pop_pos(UART_NUM_1);
                    // ESP_LOGI(TAG, "[UART PATTERN DETECTED] pos: %d, buffered size: %d", pos, buffered_size);
                    if (pos == -1) {
                        uart_flush_input(UART_NUM_1);
                    } else {
                        // uart_read_bytes(UART_NUM_1, dtmp, pos+1, 100 / portTICK_PERIOD_MS);
                        uart_read_bytes(UART_NUM_1, rx_data, buffered_size, 100/ portTICK_PERIOD_MS);
                        // *(data+buffered_size - pos-1) = '\0';
                        // ESP_LOGI(TAG, "read data: %s", dtmp);
                        // ESP_LOGI(TAG, "read pat : %s", data);

                        pchar = strtok(rx_data, "\r\n");
                        while(pchar != NULL){
                            // kiem tra ket noi wifi
                            if(!strcmp(pchar,"WIFI GOT IP")){
                                xEventGroupSetBits(eventHandler, WIFI_BIT);
                                xQueueReset(uart1_queue);
                                break;
                            }
                            else if(!strcmp(pchar, "WIFI DISCONNECT") != NULL){
                                xEventGroupClearBits(eventHandler, WIFI_BIT|TCP_BIT|SEND_BIT);
                                xQueueReset(uart1_queue);
                                break;
                            }
                            // kiem tra phan hoi ket noi tcp
                            else if(!strcmp(pchar, "CONNECT") != NULL){
                                xEventGroupSetBits(eventHandler, TCP_BIT);
                                xQueueReset(uart1_queue);
                                break;
                            }
                            else if(!strcmp(pchar, "CLOSED") || strstr(pchar, "not valid") != NULL){
                                xEventGroupClearBits(eventHandler, TCP_BIT|SEND_BIT);
                                xQueueReset(uart1_queue);
                                break;
                            }
                            ESP_LOGI(TAG, "read pat : %s", pchar);
                            pchar = strtok(NULL, "\r\n");
                        }
                        memset(rx_data, 0, strlen(rx_data));
                        uart_flush_input(UART_NUM_1);
                    }
                    break;
                //Others
                default:
                    ESP_LOGI(TAG, "uart event type: %d", event.type);
                    break;
            }
            
        }
        free(dtmp);
    }
}

// uint8_t is_succeeded(uint8_t sec_to_wait){
//     uint8_t count = 0;
//     uint8_t check = 0;
//     vTaskDelay(20/portTICK_PERIOD_MS);
//     while(!res_check && count < sec_to_wait){
//         vTaskDelay(1000/portTICK_PERIOD_MS);
//         count ++;
//     }
//     check = res_check;
//     res_check = 0;
//     return check;
// }

int sendData(const char* data){
    const int len = strlen(data);
    const int txBytes = uart_write_bytes(UART_NUM_1, data, len);
    ESP_LOGI(TAG, "Wrote %d bytes %s", txBytes, data);
    return txBytes;
}

// uint8_t send_cmd(char * cmd, uint8_t timeout){
//     sendData(cmd); 
//     return is_succeeded(timeout);  
// }

// void connect_init_esp01(){
//     // send_cmd("AT+RST");
//     uart_flush_input(UART_NUM_1);
    
//     sprintf(cmd, "AT+CWJAP=%s,%s\r\n", SSID, PWD);
//     if(send_cmd(cmd, 30)){
//         res_check=0;
//         sprintf(cmd, "AT+CIPSTART=\"TCP\",%s,%d\r\n", HOST, PORT);
//         if(send_cmd(cmd, 2)){
//             ESP_LOGI(TAG,"Start TCP/IP connection!");
//         }
//         else
//             ESP_LOGE(TAG,"Failed TCP/IP connection!");
//     }
//     vTaskDelay(1000/portTICK_PERIOD_MS);
// }

void wifi_connect_task(void *args){
    EventBits_t uxBits;
    char cmd[100];

    while(1){
        uxBits = xEventGroupWaitBits(eventHandler, WIFI_BIT, pdFALSE, pdFALSE, 0);
        if( (uxBits & WIFI_BIT) != 0){           
            ESP_LOGI(TAG, "WIFI CONNECTED");
        }
        else{
            ESP_LOGW(TAG, "WIFI DISCONNECTED");
            sprintf(cmd, "AT+CWJAP=\"%s\",\"%s\"\r\n", SSID, PWD);
            sendData(cmd);   
        }
        vTaskDelay(10000 / portTICK_PERIOD_MS);
    }
}

void tcp_establish_task(void *arg){
    EventBits_t uxBits;
    char cmd[50];
 
    while(1){
        uxBits = xEventGroupWaitBits(eventHandler, WIFI_BIT | TCP_BIT, pdFALSE, pdFALSE, 0);
        if((uxBits & (WIFI_BIT | TCP_BIT)) == WIFI_BIT ){
            sprintf(cmd, "AT+CIPSTART=\"TCP\",\"%s\",%d\r\n", HOST, PORT);
            sendData(cmd);
            ESP_LOGI(TAG, "TCP connection is establishing ....");
            vTaskDelay(1000/portTICK_PERIOD_MS);
        }
        else if((uxBits & (WIFI_BIT | TCP_BIT)) == (WIFI_BIT | TCP_BIT)){
            xEventGroupSetBits(eventHandler, SEND_BIT);
        }
        else{
            // xEventGroupClearBits(eventHandler, SEND_BIT | WIFI_BIT | TCP_BIT);
        }
        vTaskDelay(3000/portTICK_PERIOD_MS);
    }
}

void wifi_tx_task(void *arg){
    int count = 0;
    char temp[40];
    char id_string[32];
    char temp_cmd[50];
    TickType_t tick;
    

    EventBits_t uxBits;
    while(1){
        tick = xTaskGetTickCount();
        uxBits = xEventGroupWaitBits(eventHandler, SEND_BIT, pdFALSE, pdFALSE, 0);
        if((uxBits & SEND_BIT) == SEND_BIT ){
            while(xQueueReceive(beacon_queue, (void *)&beacon_data, 10)){
                count++;
                // esp_log_buffer_hex("IBEACON: Device address:", beacon_data.add, ESP_BD_ADDR_LEN );
                // esp_log_buffer_hex("IBEACON: Proximity UUID:", beacon_data.uuid, ESP_UUID_LEN_128);
                // ESP_LOGI(TAG, "Major: 0x%04x (%d)", beacon_data.major, beacon_data.major);
                // ESP_LOGI(TAG, "Minor: 0x%04x (%d)", beacon_data.minor, beacon_data.minor);
                // ESP_LOGI(TAG, "Measured power (RSSI at a 1m distance):%d ", beacon_data.tx_power);
                // ESP_LOGI(TAG, "RSSI of packet:%d dbm", beacon_data.rssi);
                convert_uint8_to_string(beacon_data.uuid, ESP_UUID_LEN_128, id_string);
                sprintf(temp, "%x,%s,%d\n", Anchor, id_string, beacon_data.rssi);
                strcat(data, temp);
                if(count == 3){
                    sprintf(temp_cmd,"AT+CIPSEND=%d\r\n", strlen(data));
                    sendData(temp_cmd);
                    vTaskDelay(70/portTICK_PERIOD_MS);
                    sendData(data);
                    memset(data, 0, strlen(data));
                    count = 0;
                }              
            }

            if(count >0){
                    sprintf(temp_cmd,"AT+CIPSEND=%d\r\n", strlen(data));
                    sendData(temp_cmd);
                    vTaskDelay(70/portTICK_PERIOD_MS);
                    sendData(data);
                    memset(data, 0, strlen(data));
                    count = 0;
                }
        }
        else{
            xQueueReset(beacon_queue);
        }
        vTaskDelayUntil(&tick, 1000/portTICK_PERIOD_MS);
    }
    
}

void app_main(void){
    // gpio_set_direction(GPIO_NUM_18, GPIO_MODE_OUTPUT);
    // gpio_set_level(GPIO_NUM_18, 0);
    const uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    uart_driver_install(UART_NUM_1, BUF_SIZE*2, BUF_SIZE*2, 50, &uart1_queue, 0);
    uart_param_config(UART_NUM_1, &uart_config);
    uart_set_pin(UART_NUM_1, TXD_PIN, RXD_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_LOGI(TAG, "[APP] Startup.. anchor: %d", Anchor);

    

    
    // gpio_set_level(RXD_PIN, 0);
    // vTaskDelay(1000/portTICK_PERIOD_MS);
    
    // gpio_set_pull_mode(RXD_PIN, GPIO_PULLUP_ONLY);

    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);

    esp_bluedroid_init();
    esp_bluedroid_enable();
    ble_beacon_appRegister();

    
    
    uart_enable_pattern_det_baud_intr(UART_NUM_1, '\n', PATTERN_CHR_NUM,9, 0 , 0);
    uart_pattern_queue_reset(UART_NUM_1, 50);


    esp_ble_gap_set_scan_params(&ble_scan_params);

    eventHandler = xEventGroupCreate();

    beacon_queue = xQueueCreate(20, sizeof(beacon_data));
    gpio_set_direction(GPIO_NUM_14, GPIO_MODE_INPUT_OUTPUT);
    gpio_set_level(GPIO_NUM_14, 1);
    gpio_set_direction(GPIO_NUM_2, GPIO_MODE_OUTPUT);
    gpio_set_level(GPIO_NUM_2, 1);
    // gpio_set_pull_mode(GPIO_NUM_14, GPIO_PULLUP_ONLY);
    gpio_hold_en(GPIO_NUM_14);

    xTaskCreatePinnedToCore(wifi_connect_task, "connect_wifi_task", 2048, NULL, 4, NULL,1);
    xTaskCreatePinnedToCore(tcp_establish_task, "tcp_task", 2048, NULL, 3, NULL, 1);
    xTaskCreatePinnedToCore(wifi_tx_task, "uart_tx_task", 2048, NULL,  1, NULL, 1);
    xTaskCreatePinnedToCore(uart_rx_task, "uart_rx_task", 2048, NULL, 5, NULL, 1);

    
}