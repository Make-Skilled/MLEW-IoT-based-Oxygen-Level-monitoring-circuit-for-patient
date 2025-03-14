// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract NotificationSystem {
    struct Notification {
        string message;
        uint256 timestamp;
        bool isRead;
        string notificationType;  // "alert", "info", "warning"
    }

    struct EmergencyContact {
        string name;
        string phone;
        string email;
        bool exists;
    }

    mapping(string => Notification[]) public userNotifications;
    mapping(string => EmergencyContact[]) public userContacts;
    mapping(string => bool) public userSubscriptions;
    address public owner;

    event NotificationCreated(string email, string message, string notificationType);
    event ContactAdded(string email, string contactName);
    event ContactUpdated(string email, string contactName);
    event ContactDeleted(string email, string contactName);
    event SubscriptionUpdated(string email, bool status);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    function addNotification(
        string memory _email,
        string memory _message,
        string memory _type
    ) public {
        Notification memory newNotification = Notification({
            message: _message,
            timestamp: block.timestamp,
            isRead: false,
            notificationType: _type
        });

        userNotifications[_email].push(newNotification);
        emit NotificationCreated(_email, _message, _type);
    }

    function addEmergencyContact(
        string memory _email,
        string memory _name,
        string memory _phone,
        string memory _contactEmail
    ) public {
        EmergencyContact memory newContact = EmergencyContact({
            name: _name,
            phone: _phone,
            email: _contactEmail,
            exists: true
        });

        userContacts[_email].push(newContact);
        emit ContactAdded(_email, _name);
    }

    function updateEmergencyContact(
        string memory _email,
        uint256 _index,
        string memory _name,
        string memory _phone,
        string memory _contactEmail
    ) public {
        require(_index < userContacts[_email].length, "Invalid contact index");
        
        EmergencyContact storage contact = userContacts[_email][_index];
        contact.name = _name;
        contact.phone = _phone;
        contact.email = _contactEmail;
        
        emit ContactUpdated(_email, _name);
    }

    function deleteEmergencyContact(
        string memory _email,
        uint256 _index
    ) public {
        require(_index < userContacts[_email].length, "Invalid contact index");
        
        // Store the contact name for the event
        string memory contactName = userContacts[_email][_index].name;
        
        // Move the last element to the deleted position
        if (_index < userContacts[_email].length - 1) {
            userContacts[_email][_index] = userContacts[_email][userContacts[_email].length - 1];
        }
        
        // Remove the last element
        userContacts[_email].pop();
        
        emit ContactDeleted(_email, contactName);
    }

    function updateSubscription(string memory _email, bool _status) public {
        userSubscriptions[_email] = _status;
        emit SubscriptionUpdated(_email, _status);
    }

    function getNotifications(string memory _email) public view returns (
        string[] memory messages,
        uint256[] memory timestamps,
        bool[] memory readStatus,
        string[] memory types
    ) {
        Notification[] memory notifications = userNotifications[_email];
        uint256 length = notifications.length;

        messages = new string[](length);
        timestamps = new uint256[](length);
        readStatus = new bool[](length);
        types = new string[](length);

        for (uint256 i = 0; i < length; i++) {
            messages[i] = notifications[i].message;
            timestamps[i] = notifications[i].timestamp;
            readStatus[i] = notifications[i].isRead;
            types[i] = notifications[i].notificationType;
        }
    }

    function getEmergencyContacts(string memory _email) public view returns (
        string[] memory names,
        string[] memory phones,
        string[] memory emails
    ) {
        EmergencyContact[] memory contacts = userContacts[_email];
        uint256 length = contacts.length;

        names = new string[](length);
        phones = new string[](length);
        emails = new string[](length);

        for (uint256 i = 0; i < length; i++) {
            names[i] = contacts[i].name;
            phones[i] = contacts[i].phone;
            emails[i] = contacts[i].email;
        }
    }

    function markNotificationAsRead(string memory _email, uint256 _index) public {
        require(_index < userNotifications[_email].length, "Invalid notification index");
        userNotifications[_email][_index].isRead = true;
    }

    function isSubscribed(string memory _email) public view returns (bool) {
        return userSubscriptions[_email];
    }
} 