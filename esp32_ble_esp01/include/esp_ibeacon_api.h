#ifndef __ESP_IBEACON_API_H__
#define __ESP_IBEACON_API_H__

#include <string.h>
#include <stdint.h>
#include <stdio.h>

#include "esp_common_api.h"

typedef struct 
{
    uint8_t length;
    uint8_t type;
    uint16_t company_id;
    uint16_t beacon_type;
}__attribute__((packed)) esp_ble_ibeacon_head_t;

typedef struct {
    uint8_t proximity_uuid[16];
    uint16_t major;
    uint16_t minor;
    int8_t measured_power;
}__attribute__((packed)) esp_ble_ibeacon_vendor_t;

typedef struct {
    esp_ble_ibeacon_head_t ibeacon_head;
    esp_ble_ibeacon_vendor_t ibeacon_vendor;
}__attribute__((packed)) esp_ble_ibeacon_t;

extern esp_ble_ibeacon_head_t ibeacon_common_head;

esp_ble_ibeacon_t* esp_ble_ibeacon_packet_decompose(uint8_t *adv_data, uint8_t pos);

#endif
