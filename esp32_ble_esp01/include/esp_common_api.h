#ifndef __ESP_COMMON_API_H__
#define __ESP_COMMON_API_H__

#include <string.h>
#include <stdint.h>
#include <stdio.h>

typedef struct 
{
    uint8_t anchor;
    uint8_t add[6];
    uint8_t uuid[16];
    uint16_t major;
    uint16_t minor;
    int8_t tx_power;
    int rssi;
}__attribute__((packed)) common_beacon_data_t;

#endif