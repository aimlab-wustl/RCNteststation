/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define ADC1_DRDY_Pin GPIO_PIN_2
#define ADC1_DRDY_GPIO_Port GPIOE
#define ADC2_DRDY_Pin GPIO_PIN_3
#define ADC2_DRDY_GPIO_Port GPIOE
#define ADC_RESET_Pin GPIO_PIN_4
#define ADC_RESET_GPIO_Port GPIOE
#define ADC2_SDOUT_Pin GPIO_PIN_5
#define ADC2_SDOUT_GPIO_Port GPIOE
#define SELB1_Pin GPIO_PIN_7
#define SELB1_GPIO_Port GPIOE
#define SELB0_Pin GPIO_PIN_8
#define SELB0_GPIO_Port GPIOE
#define SELA0_Pin GPIO_PIN_9
#define SELA0_GPIO_Port GPIOE
#define SELA1_Pin GPIO_PIN_10
#define SELA1_GPIO_Port GPIOE
#define DAC_CSn_Pin GPIO_PIN_11
#define DAC_CSn_GPIO_Port GPIOE
#define DAC_SCK_Pin GPIO_PIN_12
#define DAC_SCK_GPIO_Port GPIOE
#define DAC_SDI_Pin GPIO_PIN_14
#define DAC_SDI_GPIO_Port GPIOE
#define DIO8_Pin GPIO_PIN_8
#define DIO8_GPIO_Port GPIOD
#define DIO9_Pin GPIO_PIN_9
#define DIO9_GPIO_Port GPIOD
#define PWM_DIO12_Pin GPIO_PIN_12
#define PWM_DIO12_GPIO_Port GPIOD
#define PWM_DIO13_Pin GPIO_PIN_13
#define PWM_DIO13_GPIO_Port GPIOD
#define PWM_DIO14_Pin GPIO_PIN_14
#define PWM_DIO14_GPIO_Port GPIOD
#define PWM_DIO15_Pin GPIO_PIN_15
#define PWM_DIO15_GPIO_Port GPIOD
#define DIO0_Pin GPIO_PIN_0
#define DIO0_GPIO_Port GPIOD
#define DIO1_Pin GPIO_PIN_1
#define DIO1_GPIO_Port GPIOD
#define DIO2_Pin GPIO_PIN_2
#define DIO2_GPIO_Port GPIOD
#define DIO3_Pin GPIO_PIN_3
#define DIO3_GPIO_Port GPIOD
#define DIO4_Pin GPIO_PIN_4
#define DIO4_GPIO_Port GPIOD
#define DIO5_Pin GPIO_PIN_5
#define DIO5_GPIO_Port GPIOD
#define DIO6_Pin GPIO_PIN_6
#define DIO6_GPIO_Port GPIOD
#define DIO7_Pin GPIO_PIN_7
#define DIO7_GPIO_Port GPIOD
#define ADC2_CS_Pin GPIO_PIN_0
#define ADC2_CS_GPIO_Port GPIOE
#define ADC1_CS_Pin GPIO_PIN_1
#define ADC1_CS_GPIO_Port GPIOE

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
