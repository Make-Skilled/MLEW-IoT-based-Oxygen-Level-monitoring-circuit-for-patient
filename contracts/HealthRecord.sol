// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract HealthRecord {
    struct HealthData {
        uint256 timestamp;
        uint32 temperature;  // Stored as temperature * 100
        uint32 heartRate;
        uint32 spo2;
        string deviceId;
    }
    
    struct Alert {
        string alertType;
        string message;
        uint256 timestamp;
    }
    
    mapping(string => HealthData[]) public deviceRecords;
    mapping(string => Alert[]) public deviceAlerts;
    
    event NewHealthData(string deviceId, uint256 timestamp);
    event AlertGenerated(string deviceId, string alertType);
    
    // Store health data
    function recordHealthData(
        string memory deviceId,
        uint32 temperature,
        uint32 heartRate,
        uint32 spo2
    ) public {
        HealthData memory newData = HealthData(
            block.timestamp,
            temperature,
            heartRate,
            spo2,
            deviceId
        );
        
        deviceRecords[deviceId].push(newData);
        
        // Check for alerts
        checkVitalSigns(deviceId, temperature, heartRate, spo2);
        
        emit NewHealthData(deviceId, block.timestamp);
    }
    
    // Check vital signs and generate alerts
    function checkVitalSigns(
        string memory deviceId,
        uint32 temperature,
        uint32 heartRate,
        uint32 spo2
    ) private {
        if (temperature > 3780) { // 37.8°C
            generateAlert(deviceId, "High Temperature", "Temperature above normal range");
        }
        if (heartRate > 100) {
            generateAlert(deviceId, "High Heart Rate", "Heart rate above normal range");
        }
        if (spo2 < 95) {
            generateAlert(deviceId, "Low SpO2", "Blood oxygen below normal range");
        }
    }
    
    // Generate alert
    function generateAlert(
        string memory deviceId,
        string memory alertType,
        string memory message
    ) private {
        Alert memory newAlert = Alert(alertType, message, block.timestamp);
        deviceAlerts[deviceId].push(newAlert);
        emit AlertGenerated(deviceId, alertType);
    }
    
    // Get latest health data for a device
    function getLatestData(string memory deviceId) 
        public 
        view 
        returns (HealthData memory) 
    {
        require(deviceRecords[deviceId].length > 0, "No data found");
        return deviceRecords[deviceId][deviceRecords[deviceId].length - 1];
    }
} 