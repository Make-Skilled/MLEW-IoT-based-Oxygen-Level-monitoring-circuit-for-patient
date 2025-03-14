# IoT Health Monitoring System with Blockchain

A decentralized health monitoring system that uses IoT devices to track vital signs and store data securely on the blockchain. The system provides real-time monitoring, alerts, and emergency contact management.

## Features

### 1. Health Monitoring
- Real-time monitoring of vital signs:
  - Heart Rate
  - Blood Oxygen Level (SpO2)
  - Body Temperature
- Customizable threshold settings for alerts
- Historical data tracking
- Real-time data visualization

### 2. User Management
- Secure user registration and authentication
- Profile management
- Password protection
- Customizable health monitoring settings
- All user data stored securely on the blockchain

### 3. Notification System
- Real-time health alerts
- Different notification types:
  - Health alerts (critical)
  - Warnings (concerning)
  - Information updates
- Read/unread status tracking
- Timestamp tracking
- Visual indicators for different notification types

### 4. Emergency Contacts
- Add and manage emergency contacts
- Store contact information securely on the blockchain
- Quick access to emergency contact information
- Automatic notification of emergency contacts during critical situations

### 5. Blockchain Integration
- Secure data storage on Ethereum blockchain
- Immutable health records
- Transparent data access
- Smart contract-based data management
- Event logging for all actions

### 6. IoT Integration
- ESP32 microcontroller support
- MAX30100 sensor integration
- Real-time data transmission
- Automatic data collection and storage

## Technical Stack

### Backend
- Python Flask
- Web3.py for blockchain interaction
- RESTful API endpoints
- Session management
- CORS support

### Frontend
- HTML5
- CSS3 (Bootstrap 5)
- JavaScript
- Responsive design
- Real-time updates

### Blockchain
- Solidity smart contracts
- Ethereum (Ganache for development)
- Web3.js integration
- Smart contract events

### IoT
- ESP32 microcontroller
- MAX30100 sensor
- Arduino IDE
- WiFi connectivity

## Project Structure

```
project/
├── contracts/
│   ├── HealthRecord.sol
│   ├── UserManagement.sol
│   └── NotificationSystem.sol
├── server/
│   ├── app.py
│   ├── templates/
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── notifications.html
│   │   └── emergency_contacts.html
│   └── static/
│       └── images/
├── build/
│   └── contracts/
│       ├── HealthRecord.json
│       ├── UserManagement.json
│       └── NotificationSystem.json
└── README.md
```

## Setup Instructions

### Prerequisites
1. Python 3.8+
2. Node.js and npm
3. Ganache
4. MetaMask
5. Arduino IDE
6. ESP32 development board
7. MAX30100 sensor

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd health-monitoring-system
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

4. Deploy smart contracts:
```bash
truffle compile
truffle migrate --network development
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application

1. Start Ganache:
```bash
ganache-cli
```

2. Start the Flask server:
```bash
cd server
python app.py
```

3. Access the application:
```
http://localhost:5000
```

### IoT Setup

1. Install required libraries in Arduino IDE:
   - MAX30100
   - WiFiManager
   - WebSockets

2. Configure ESP32:
   - Upload the code to ESP32
   - Connect MAX30100 sensor
   - Configure WiFi settings

## Smart Contracts

### HealthRecord.sol
- Stores health monitoring data
- Manages device data
- Handles data retrieval

### UserManagement.sol
- User registration and authentication
- Profile management
- Settings storage

### NotificationSystem.sol
- Notification management
- Emergency contact storage
- Alert system

## API Endpoints

### Health Data
- POST /api/health-data
- GET /api/health-data/latest
- GET /api/alerts/<device_id>

### User Management
- POST /login
- POST /signup
- GET /profile
- POST /profile/update
- POST /profile/settings
- POST /profile/password

### Notifications
- GET /notifications
- POST /notifications/mark-read/<index>
- GET /emergency-contacts
- POST /emergency-contacts/add
- POST /subscription/update

## Security Features

1. Blockchain-based data storage
2. Password hashing
3. Session management
4. Input validation
5. CORS protection
6. Secure API endpoints
7. Encrypted data transmission

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ESP32 community
- Ethereum community
- Bootstrap team
- Flask team 