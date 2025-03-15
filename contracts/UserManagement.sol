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

    // Main storage mappings
    mapping(string => User) private users;  // email -> User
    mapping(address => string) public walletToEmail;  // wallet -> email

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
    }

    function verifyLogin(string memory _email, bytes32 _passwordHash) public view returns (bool) {
        require(users[_email].exists, "User does not exist");
        return users[_email].passwordHash == _passwordHash;
    }

    function checkUser(string memory _email) public view returns (bool) {
        return users[_email].exists;
    }

    function getUser(string memory _email) public view returns (
        string memory name,
        address walletAddress
    ) {
        require(users[_email].exists, "User does not exist");
        User memory user = users[_email];
        return (user.name, user.walletAddress);
    }
}
