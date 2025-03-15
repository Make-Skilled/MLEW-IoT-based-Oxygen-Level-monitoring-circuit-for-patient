
from flask import Flask, request, jsonify, render_template, session, redirect, url_for,jsonify
from flask_cors import CORS
import requests
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import json
import os
import bcrypt
from functools import wraps
from datetime import datetime


# Get the absolute path to the server directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
CORS(app)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Blockchain configuration
BLOCKCHAIN_SERVER = "http://127.0.0.1:7545"
HEALTH_RECORD_ARTIFACT_PATH = "./build/contracts/HealthRecord.json"
USER_MANAGEMENT_ARTIFACT_PATH = "./build/contracts/UserManagement.json"
NOTIFICATION_SYSTEM_ARTIFACT_PATH = "./build/contracts/NotificationSystem.json"

def connect_with_contract(wallet_address=None, artifact=USER_MANAGEMENT_ARTIFACT_PATH):
    try:
        # Connect to blockchain server
        web3 = Web3(HTTPProvider(BLOCKCHAIN_SERVER))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        print(f'Connected with Blockchain Server: {BLOCKCHAIN_SERVER}')

        # Set default account based on wallet address
        if wallet_address and web3.isAddress(wallet_address):
            web3.eth.default_account = wallet_address
        else:
            web3.eth.default_account = web3.eth.accounts[0]
        print(f'Using wallet address: {web3.eth.default_account}')

        # Load contract artifact
        with open(artifact) as f:
            artifact_json = json.load(f)
            contract_abi = artifact_json['abi']
            contract_address = artifact_json['networks']['5777']['address']
            print(f'Loading contract from: {artifact}')
            print(f'Contract address: {contract_address}')

        # Create contract instance
        contract = web3.eth.contract(abi=contract_abi, address=contract_address)
        return contract, web3

    except Exception as e:
        print(f"Error in connect_with_contract: {str(e)}")
        raise

# Initialize contract connections with default account (0)
try:
    health_contract, health_web3 = connect_with_contract(0, HEALTH_RECORD_ARTIFACT_PATH)
    user_contract, user_web3 = connect_with_contract(0, USER_MANAGEMENT_ARTIFACT_PATH)
    notification_contract, notification_web3 = connect_with_contract(0, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
    print("All contracts initialized successfully")
except Exception as e:
    print(f"Error initializing contracts: {str(e)}")
    raise

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not all([email, password]):
                return render_template('login.html', error='All fields are required')
            
            try:
                # Check if user exists
                user_exists = user_contract.functions.checkUser(email).call()
                if not user_exists:
                    return render_template('login.html', error='User not found')
                
                # Hash the password
                password_hash = Web3.keccak(text=password).hex()
                if not password_hash.startswith('0x'):
                    password_hash = '0x' + password_hash
                
                # Verify login
                is_valid = user_contract.functions.verifyLogin(
                    email,
                    Web3.toBytes(hexstr=password_hash)
                ).call()
                
                if is_valid:
                    # Get user data
                    name, wallet_address = user_contract.functions.getUser(email).call()
                    print(name, wallet_address)
                    # Set session data
                    session['user_id'] = email
                    session['wallet_address'] = wallet_address
                    session['user_name'] = name
                    print(session['wallet_address'])
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error='Invalid password')
                    
            except Exception as contract_error:
                print(f"Contract interaction error: {str(contract_error)}")
                return render_template('login.html', error='Login failed. Please try again.')
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            return render_template('login.html', error='Login failed')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            wallet_address = request.form.get('wallet_address')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not all([name, email, wallet_address, password, confirm_password]):
                return render_template('signup.html', error='All fields are required')
                
            if password != confirm_password:
                return render_template('signup.html', error='Passwords do not match')
            
            if not Web3.isAddress(wallet_address):
                return render_template('signup.html', error='Invalid wallet address')

            # Create contract instance with user's wallet
            user_contract_instance, web3 = connect_with_contract(wallet_address)
            
            # Hash the password
            password_hash = Web3.keccak(text=password).hex()
            if not password_hash.startswith('0x'):
                password_hash = '0x' + password_hash
            
            try:
                # Register user
                tx = user_contract_instance.functions.registerUser(
                    email,
                    name,
                    Web3.toBytes(hexstr=password_hash),
                    wallet_address
                ).transact({
                    'from': wallet_address,
                    'gas': 3000000,
                    'gasPrice': web3.eth.gas_price
                })
                
                # Wait for transaction receipt
                receipt = web3.eth.wait_for_transaction_receipt(tx)
                
                if receipt.status == 1:
                    # Set session data
                    session['user_id'] = email
                    session['wallet_address'] = wallet_address
                    session['user_name'] = name
                    
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('signup.html', error='Transaction failed')
                    
            except Exception as contract_error:
                print(f"Contract interaction error: {str(contract_error)}")
                return render_template('signup.html', error='Registration failed. Please try again.')
                
        except Exception as e:
            print(f"Signup error: {str(e)}")
            return render_template('signup.html', error='Registration failed')
    
    return render_template('signup.html')

@app.route('/signup/complete', methods=['POST'])
def complete_signup():
    try:
        data = request.get_json()
        signed_tx = data.get('signedTransaction')
        user_data = data.get('userData')
        
        if not signed_tx or not user_data:
            return jsonify({'status': 'error', 'message': 'Missing transaction data'}), 400
        
        web3 = Web3(HTTPProvider(BLOCKCHAIN_SERVER))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)  # Add this line for POA networks
        
        try:
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_tx)
            
            # Wait for transaction confirmation with timeout
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)  # 2 minutes timeout
            
            if receipt.status == 1:  # Transaction successful
                session['user_id'] = user_data['email']
                session['wallet_address'] = user_data['wallet_address']
                session['user_name'] = user_data['name']
                
                return jsonify({
                    'status': 'success',
                    'redirect': url_for('dashboard')
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Transaction failed'
                }), 500
                
        except Exception as tx_error:
            print(f"Transaction error: {str(tx_error)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to process blockchain transaction'
            }), 500
            
    except Exception as e:
        print(f"Complete signup error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        wallet_address = session['wallet_address']
        health_record_contract, health_web3 = connect_with_contract(wallet_address, HEALTH_RECORD_ARTIFACT_PATH)
        
        # Get latest health data
        try:
            # Get latest record for the user's wallet address
            latest_record = health_record_contract.functions.getLatestRecord(wallet_address).call()
            
            # Parse the returned data based on contract structure
            formatted_data = {
                "timestamp": latest_record[0],
                "temperature": float(latest_record[1]),  # Convert string to float
                "heart_rate": int(latest_record[2]),    # Convert string to int
                "spo2": int(latest_record[3]),          # Convert string to int
                "systolic": float(latest_record[4]),    # Convert string to float
                "diastolic": float(latest_record[5])    # Convert string to float
            }

            # Add status indicators based on normal ranges
            vital_status = {
                "temperature": "normal" if 36.1 <= formatted_data["temperature"] <= 37.2 else "abnormal",
                "heart_rate": "normal" if 60 <= formatted_data["heart_rate"] <= 100 else "abnormal",
                "spo2": "normal" if formatted_data["spo2"] >= 95 else "abnormal",
                "systolic": "normal" if 90 <= formatted_data["systolic"] <= 120 else "abnormal",
                "diastolic": "normal" if 60 <= formatted_data["diastolic"] <= 80 else "abnormal"
            }
            formatted_data.update({"status": vital_status})

        except Exception as data_error:
            print(f"Error getting health data: {str(data_error)}")
            formatted_data = {
                "timestamp": None,
                "temperature": None,
                "heart_rate": None,
                "spo2": None,
                "systolic": None,
                "diastolic": None,
                "status": {}
            }
        
        # Get notifications/alerts
        try:
            notification_contract, notification_web3 = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
            messages, timestamps, read_status, types = notification_contract.functions.getNotifications(session['user_id']).call()
            alerts = []
            for i in range(len(messages)):
                alerts.append({
                    'message': messages[i],
                    'timestamp': datetime.fromtimestamp(int(timestamps[i])).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': types[i]
                })
        except Exception as alert_error:
            print(f"Error getting alerts: {str(alert_error)}")
            alerts = []
        
        return render_template('dashboard.html', 
                             latest_data=formatted_data,
                             alerts=alerts,
                             user_name=session.get('user_name'))
                             
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        return render_template('dashboard.html', 
                             error=str(e),
                             latest_data={
                                 "timestamp": None,
                                 "temperature": None,
                                 "heart_rate": None,
                                 "spo2": None,
                                 "systolic": None,
                                 "diastolic": None,
                                 "status": {}
                             },
                             alerts=[],
                             user_name=session.get('user_name'))

def calculate_change(current, normal):
    """Calculate percentage change from normal value"""
    if normal == 0:
        return 0
    return round(((current - normal) / normal) * 100, 1)

@app.route('/logout')
def logout():
    # Clear all session variables
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user_email = session['user_id']
    
    try:
        # Get user data from blockchain
        name, email, wallet_address = user_contract.functions.getUser(user_email).call()
        
        # Get user settings from blockchain
        try:
            hr_high, hr_low, spo2_low, temp_high, temp_low = user_contract.functions.getUserSettings(user_email).call()
            settings = {
                'hr_high': hr_high,
                'hr_low': hr_low,
                'spo2_low': spo2_low,
                'temp_high': temp_high / 100,  # Convert back from integer
                'temp_low': temp_low / 100     # Convert back from integer
            }
        except:
            # Default settings if not set
            settings = {
                'hr_high': 100,
                'hr_low': 60,
                'spo2_low': 95,
                'temp_high': 37.8,
                'temp_low': 35.0
            }
        
        return render_template('profile.html', 
                             user={'name': name, 'email': email, 'wallet_address': wallet_address},
                             settings=settings)
                             
    except Exception as e:
        print(f"Profile error: {str(e)}")
        return render_template('profile.html', error=f'Error loading profile: {str(e)}')

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user_email = session['user_id']
    wallet_address = session['wallet_address']
    name = request.form.get('name')
    
    try:
        # Update user on blockchain
        tx_hash = user_contract.functions.updateUser(user_email, name).transact({
            'from': wallet_address
        })
        
        # Wait for transaction receipt
        receipt = user_web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:  # Transaction successful
            return redirect(url_for('profile'))
        else:
            return jsonify({'status': 'error', 'message': 'Transaction failed'}), 500
        
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/sensorData")
def sensor_data():
    print("Sensor data route accessed")
    print(session['wallet_address'])
    try:
        # Get sensor data from request parameters
        temp = float(request.args.get('temp'))
        hr = int(request.args.get('hr'))
        spo2 = int(request.args.get('spo2'))
        systolic = float(request.args.get('systolic'))
        diastolic = float(request.args.get('diastolic'))
        
        # Validate parameters existence
        if not all([temp, hr, spo2, systolic, diastolic]):
            return jsonify({
                'status': 'error',
                'message': 'Missing parameters'
            }), 400

        # Define normal ranges for vital signs
        VITAL_RANGES = {
            'temperature': {'min': 36.1, 'max': 37.2, 
                          'mild': {'min': 35.0, 'max': 38.5},
                          'severe': {'min': 34.0, 'max': 39.5}},
            'heart_rate': {'min': 60, 'max': 100,
                          'mild': {'min': 50, 'max': 120},
                          'severe': {'min': 40, 'max': 140}},
            'spo2': {'min': 95, 'max': 100,
                    'mild': {'min': 90, 'max': 100},
                    'severe': {'min': 85, 'max': 100}},
            'systolic': {'min': 90, 'max': 120,
                        'mild': {'min': 80, 'max': 140},
                        'severe': {'min': 70, 'max': 160}},
            'diastolic': {'min': 60, 'max': 80,
                         'mild': {'min': 50, 'max': 90},
                         'severe': {'min': 40, 'max': 100}}
        }

        def check_vital_severity(value, ranges, vital_name):
            if ranges['min'] <= value <= ranges['max']:
                return None
            elif ranges['mild']['min'] <= value <= ranges['mild']['max']:
                return {
                    'level': 'MILD',
                    'message': f'Mild abnormality in {vital_name}: {value}',
                    'parameter': vital_name,
                    'value': str(value)
                }
            else:
                return {
                    'level': 'SEVERE',
                    'message': f'Severe abnormality in {vital_name}: {value}',
                    'parameter': vital_name,
                    'value': str(value)
                }

        # Check each vital sign and collect abnormalities
        abnormalities = []
        
        temp_status = check_vital_severity(temp, VITAL_RANGES['temperature'], 'Temperature')
        if temp_status:
            abnormalities.append(temp_status)
            
        hr_status = check_vital_severity(hr, VITAL_RANGES['heart_rate'], 'Heart Rate')
        if hr_status:
            abnormalities.append(hr_status)
            
        spo2_status = check_vital_severity(spo2, VITAL_RANGES['spo2'], 'SpO2')
        if spo2_status:
            abnormalities.append(spo2_status)
            
        systolic_status = check_vital_severity(systolic, VITAL_RANGES['systolic'], 'Systolic BP')
        if systolic_status:
            abnormalities.append(systolic_status)
            
        diastolic_status = check_vital_severity(diastolic, VITAL_RANGES['diastolic'], 'Diastolic BP')
        if diastolic_status:
            abnormalities.append(diastolic_status)

        try:
            # Get current timestamp
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Connect to notification contract
            notification_contract, web3 = connect_with_contract(session['wallet_address'], NOTIFICATION_SYSTEM_ARTIFACT_PATH)

            # Add notifications for each abnormality
            for abnormality in abnormalities:
                notification_contract.functions.addNotification(
                    session['wallet_address'],
                    abnormality['message'],
                    current_timestamp,
                    abnormality['parameter'],
                    abnormality['value'],
                    abnormality['level']
                ).transact()

            # Store sensor data in health record contract
            health_contract, web3 = connect_with_contract(session['wallet_address'], HEALTH_RECORD_ARTIFACT_PATH)
            
            # Convert numeric values to strings as per contract requirements
            tx_hash = health_contract.functions.addHealthRecord(
                current_timestamp,                    # _timestamp
                str(temp),                           # _temperature
                str(hr),                             # _heartRate
                str(spo2),                           # _spo2
                str(systolic),                       # _systolic
                str(diastolic),                      # _diastolic
                str(session['wallet_address'])           # _wallet
            ).transact()

            return jsonify({
                'status': 'success',
                'message': 'Health data recorded successfully',
                'abnormalities': abnormalities,
                'tx_hash': tx_hash.hex()
            })

        except Exception as contract_error:
            print(f"Contract interaction error: {str(contract_error)}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to record health data: {str(contract_error)}'
            }), 500
            
    except Exception as e:
        print(f"Sensor data processing error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing sensor data: {str(e)}'
        }), 500

@app.route('/notifications')
@login_required
def notifications():
    print("Notifications route accessed")
    try:
        wallet_address = session['wallet_address']
        print(f"Wallet address: {wallet_address}")
        notification_contract, _ = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        
        # Get notifications from blockchain
        messages, timestamps, abnormal_params, param_values, warning_levels = (
            notification_contract.functions.getNotifications(wallet_address).call()
        )
        
        # Format notifications
        notifications = []
        for i in range(len(messages)):
            notification_type = "alert" if warning_levels[i] == "HIGH" else (
                "warning" if warning_levels[i] == "MEDIUM" else "info"
            )
            
            notifications.append({
                'index': i,
                'message': messages[i],
                'timestamp': datetime.fromtimestamp(int(timestamps[i])).strftime('%Y-%m-%d %H:%M:%S'),
                'abnormal_parameter': abnormal_params[i],
                'parameter_value': param_values[i],
                'type': notification_type,
                'warning_level': warning_levels[i]
            })
            
        # Sort notifications by timestamp (newest first)
        notifications.sort(key=lambda x: x['timestamp'], reverse=True)
                
        return render_template('notifications.html', 
                             notifications=notifications)
                             
    except Exception as e:
        print(f"Notifications error: {str(e)}")
        return render_template('notifications.html', 
                             error=f'Error loading notifications: {str(e)}',
                             notifications=[]
                             )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 