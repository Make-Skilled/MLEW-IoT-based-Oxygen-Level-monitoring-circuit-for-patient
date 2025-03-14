// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract NotificationSystem {
    struct Notification {
        address wallet;
        string message;
        string timestamp;
        string abnormalParameter;
        string parameterValue;
        string warningLevel;  // "LOW", "MEDIUM", "HIGH"
    }

    // Mapping from wallet address to array of notifications
    mapping(address => Notification[]) private userNotifications;
    
    // Mapping to track total notifications for each wallet
    mapping(address => uint256) private totalNotifications;

    function addNotification(
        address _wallet,
        string memory _message,
        string memory _timestamp,
        string memory _abnormalParameter,
        string memory _parameterValue,
        string memory _warningLevel
    ) public {
        // Create new notification
        Notification memory newNotification = Notification({
            wallet: _wallet,
            message: _message,
            timestamp: _timestamp,
            abnormalParameter: _abnormalParameter,
            parameterValue: _parameterValue,
            warningLevel: _warningLevel
        });

        // Add notification to user's notifications array
        userNotifications[_wallet].push(newNotification);
        
        // Update counter
        totalNotifications[_wallet]++;
    }

    function getNotifications(address _wallet) public view returns (
        string[] memory messages,
        string[] memory timestamps,
        string[] memory abnormalParameters,
        string[] memory parameterValues,
        string[] memory warningLevels
    ) {
        uint256 length = userNotifications[_wallet].length;
        
        // Initialize arrays with the correct length
        messages = new string[](length);
        timestamps = new string[](length);
        abnormalParameters = new string[](length);
        parameterValues = new string[](length);
        warningLevels = new string[](length);

        // Populate arrays with notification data
        for (uint256 i = 0; i < length; i++) {
            Notification storage notification = userNotifications[_wallet][i];
            messages[i] = notification.message;
            timestamps[i] = notification.timestamp;
            abnormalParameters[i] = notification.abnormalParameter;
            parameterValues[i] = notification.parameterValue;
            warningLevels[i] = notification.warningLevel;
        }

        return (messages, timestamps, abnormalParameters, parameterValues, warningLevels);
    }

    function getNotificationCount(address _wallet) public view returns (uint256 total) {
        return totalNotifications[_wallet];
    }

    function getNotificationByIndex(address _wallet, uint256 _index) public view returns (
        string memory message,
        string memory timestamp,
        string memory abnormalParameter,
        string memory parameterValue,
        string memory warningLevel
    ) {
        require(_index < userNotifications[_wallet].length, "Invalid notification index");
        
        Notification storage notification = userNotifications[_wallet][_index];
        
        return (
            notification.message,
            notification.timestamp,
            notification.abnormalParameter,
            notification.parameterValue,
            notification.warningLevel
        );
    }
}
