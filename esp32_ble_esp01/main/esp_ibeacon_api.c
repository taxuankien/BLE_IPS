#include <stdio.h>
#include <stdint.h>

#include "esp_common_api.h"
#include "esp_ibeacon_api.h"



esp_ble_ibeacon_t* esp_ble_ibeacon_packet_decompose(uint8_t *adv_data, uint8_t pos){
    return (esp_ble_ibeacon_t*)(adv_data+pos);
}