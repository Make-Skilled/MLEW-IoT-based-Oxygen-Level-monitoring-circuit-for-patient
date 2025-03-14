// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract UserManagement {
    struct User {
        string name;
        string email;
        bytes32 passwordHash;
        address walletAddress;
        bool exists;
    }

    struct UserSettings {
        uint256 hrHigh;
        uint256 hrLow;
        uint256 spo2Low;
        uint256 tempHigh;
        uint256 tempLow;
        bool exists;
    }

    mapping(string => User) public users;
    mapping(string => UserSettings) public userSettings;
    mapping(address => string) public walletToEmail;
    address public owner;

    event UserRegistered(string email, string name, address walletAddress);
    event UserUpdated(string email, string name);
    event SettingsUpdated(string email);
    event PasswordChanged(string email);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    function registerUser(
        string memory _email, 
        string memory _name, 
        bytes32 _passwordHash,
        address _walletAddress
    ) public {
        require(!users[_email].exists, "User already exists");
        require(bytes(walletToEmail[_walletAddress]).length == 0, "Wallet address already registered");
        
        users[_email] = User({
            name: _name,
            email: _email,
            passwordHash: _passwordHash,
            walletAddress: _walletAddress,
            exists: true
        });

        walletToEmail[_walletAddress] = _email;
        emit UserRegistered(_email, _name, _walletAddress);
    }

    function updateUser(string memory _email, string memory _name) public {
        require(users[_email].exists, "User does not exist");
        require(msg.sender == users[_email].walletAddress, "Only wallet owner can update profile");
        
        users[_email].name = _name;
        emit UserUpdated(_email, _name);
    }

    function updateSettings(
        string memory _email,
        uint256 _hrHigh,
        uint256 _hrLow,
        uint256 _spo2Low,
        uint256 _tempHigh,
        uint256 _tempLow
    ) public {
        require(users[_email].exists, "User does not exist");
        require(msg.sender == users[_email].walletAddress, "Only wallet owner can update settings");
        
        userSettings[_email] = UserSettings({
            hrHigh: _hrHigh,
            hrLow: _hrLow,
            spo2Low: _spo2Low,
            tempHigh: _tempHigh,
            tempLow: _tempLow,
            exists: true
        });

        emit SettingsUpdated(_email);
    }

    function changePassword(string memory _email, bytes32 _newPasswordHash) public {
        require(users[_email].exists, "User does not exist");
        require(msg.sender == users[_email].walletAddress, "Only wallet owner can change password");
        
        users[_email].passwordHash = _newPasswordHash;
        emit PasswordChanged(_email);
    }

    function getUser(string memory _email) public view returns (
        string memory name, 
        string memory email,
        address walletAddress
    ) {
        require(users[_email].exists, "User does not exist");
        return (users[_email].name, users[_email].email, users[_email].walletAddress);
    }

    function getUserWallet(string memory _email) public view returns (address) {
        require(users[_email].exists, "User does not exist");
        return users[_email].walletAddress;
    }

    function getUserSettings(string memory _email) public view returns (
        uint256 hrHigh,
        uint256 hrLow,
        uint256 spo2Low,
        uint256 tempHigh,
        uint256 tempLow
    ) {
        require(users[_email].exists, "User does not exist");
        require(userSettings[_email].exists, "Settings do not exist");
        
        UserSettings memory settings = userSettings[_email];
        return (
            settings.hrHigh,
            settings.hrLow,
            settings.spo2Low,
            settings.tempHigh,
            settings.tempLow
        );
    }

    function verifyPassword(string memory _email, bytes32 _passwordHash) public view returns (bool) {
        require(users[_email].exists, "User does not exist");
        return users[_email].passwordHash == _passwordHash;
    }
} 