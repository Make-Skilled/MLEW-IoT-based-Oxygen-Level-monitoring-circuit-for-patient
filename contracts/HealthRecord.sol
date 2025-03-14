// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract HealthRecord {
    struct HealthData {
        string timestamp;
        string temperature;
        string heartRate;
        string spo2;
        string systolic;
        string diastolic;
        address wallet;
    }

    // Mapping from wallet address to array of health records
    mapping(address => HealthData[]) private patientRecords;
    
    // Mapping to track the latest record index for each patient
    mapping(address => uint256) private latestRecordIndex;
    
    // Mapping to track total records for each patient
    mapping(address => uint256) private totalRecords;

    function addHealthRecord(
        string memory _timestamp,
        string memory _temperature,
        string memory _heartRate,
        string memory _spo2,
        string memory _systolic,
        string memory _diastolic,
        address _wallet
    ) public {
        // Create new health record
        HealthData memory newRecord = HealthData({
            timestamp: _timestamp,
            temperature: _temperature,
            heartRate: _heartRate,
            spo2: _spo2,
            systolic: _systolic,
            diastolic: _diastolic,
            wallet: _wallet
        });

        // Add record to patient's records array
        patientRecords[_wallet].push(newRecord);
        
        // Update latest record index and total records
        latestRecordIndex[_wallet] = patientRecords[_wallet].length - 1;
        totalRecords[_wallet]++;
    }

    function getLatestRecord(address _wallet) public view returns (
        string memory timestamp,
        string memory temperature,
        string memory heartRate,
        string memory spo2,
        string memory systolic,
        string memory diastolic
        
    ) {
        // Check if patient has any records
        require(totalRecords[_wallet] > 0, "No records found for this patient");

        // Get the latest record
        HealthData memory latest = patientRecords[_wallet][latestRecordIndex[msg.sender]];

        return (
            latest.timestamp,
            latest.temperature,
            latest.heartRate,
            latest.spo2,
            latest.systolic,
            latest.diastolic
        );
    }

    function getRecordCount() public view returns (uint256) {
        return totalRecords[msg.sender];
    }

    // Optional: Get record by index
    function getRecordByIndex(uint256 index) public view returns (
        string memory timestamp,
        string memory temperature,
        string memory heartRate,
        string memory spo2,
        string memory systolic,
        string memory diastolic
    ) {
        require(index < totalRecords[msg.sender], "Index out of bounds");
        
        HealthData memory record = patientRecords[msg.sender][index];
        
        return (
            record.timestamp,
            record.temperature,
            record.heartRate,
            record.spo2,
            record.systolic,
            record.diastolic
        );
    }
}
