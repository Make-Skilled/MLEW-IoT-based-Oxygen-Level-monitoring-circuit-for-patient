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
HEALTH_RECORD_ARTIFACT_PATH = "../build/contracts/HealthRecord.json"
USER_MANAGEMENT_ARTIFACT_PATH = "../build/contracts/UserManagement.json"
NOTIFICATION_SYSTEM_ARTIFACT_PATH = "../build/contracts/NotificationSystem.json"

def connect_with_contract(wallet_address=None, artifact=USER_MANAGEMENT_ARTIFACT_PATH):
    # Connect to blockchain server
    web3 = Web3(HTTPProvider(BLOCKCHAIN_SERVER))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    print('Connected with Blockchain Server')

    # Set default account based on wallet address
    if wallet_address and web3.isAddress(wallet_address):
        web3.eth.default_account = wallet_address
    else:
        web3.eth.default_account = web3.eth.accounts[0]
    print('Wallet Selected:', web3.eth.default_account)

    # Load contract artifact
    with open(artifact) as f:
        artifact_json = json.load(f)
        contract_abi = artifact_json['abi']
        contract_address = artifact_json['networks']['5777']['address']
    
    # Create contract instance
    contract = web3.eth.contract(abi=contract_abi, address=contract_address)
    print('Contract Selected:', contract_address)
    return contract, web3

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
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([email, password]):
            return render_template('login.html', error='All fields are required')
        
        try:
            # Hash the password
            password_hash = user_web3.keccak(text=password).hex()
            
            # Verify password on blockchain
            if user_contract.functions.verifyPassword(email, password_hash).call():
                # Get user's wallet address and name
                wallet_address = user_contract.functions.getUserWallet(email).call()
                name, _, _ = user_contract.functions.getUser(email).call()
                
                # Set session variables
                session['user_id'] = email
                session['wallet_address'] = wallet_address
                session['user_name'] = name
                session.permanent = True  # Make session last longer
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid credentials')
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            return render_template('login.html', error='Login failed. Please try again.')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        wallet_address = request.form.get('wallet_address')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input fields
        if not all([name, email, wallet_address, password, confirm_password]):
            return render_template('signup.html', error='All fields are required')
            
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        try:
            # # Hash the password using bcrypt
            # password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Convert the password hash to bytes32
            password_hash_bytes32 = Web3.toHex(Web3.keccak(text=password)).rjust(66, '0')  # Ensure it is 32 bytes
            
            # Create contract instance with user's wallet
            user_contract_instance, web3 = connect_with_contract(wallet_address)
            
            # Register user on blockchain
            tx = user_contract_instance.functions.registerUser(
                email, 
                name, 
                password_hash_bytes32,  # Use the bytes32 password hash
                wallet_address
            ).buildTransaction({
                'from': wallet_address,
                'nonce': web3.eth.get_transaction_count(wallet_address),
                'gas': 2000000,
                'gasPrice': web3.eth.gas_price
            })
            
            # Send the transaction
            tx_hash = web3.eth.send_raw_transaction(web3.eth.account.sign_transaction(tx, private_key).rawTransaction)
            
            # Return the transaction data to the frontend for signing
            return jsonify({
                'status': 'success',
                'transaction': {
                    'to': tx['to'],
                    'from': tx['from'],
                    'data': tx['data'],
                    'gas': tx['gas'],
                    'gasPrice': tx['gasPrice'],
                    'nonce': tx['nonce'],
                    'chainId': web3.eth.chain_id
                }
            })
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            return render_template('signup.html', error=f'Registration failed: {str(e)}')
    
    return render_template('signup.html')

@app.route('/signup/complete', methods=['POST'])
def complete_signup():
    try:
        # Get the signed transaction from the frontend
        signed_tx = request.json.get('signedTransaction')
        user_data = request.json.get('userData')
        
        if not signed_tx or not user_data:
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400
            
        # Send the signed transaction
        web3 = Web3(HTTPProvider(BLOCKCHAIN_SERVER))
        tx_hash = web3.eth.send_raw_transaction(signed_tx)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:  # Transaction successful
            # Set session variables
            session['user_id'] = user_data['email']
            session['wallet_address'] = user_data['wallet_address']
            session['user_name'] = user_data['name']
            session.permanent = True
            
            return jsonify({
                'status': 'success',
                'redirect': url_for('dashboard')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Transaction failed'
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
        # Ensure you are unpacking the return values correctly
        health_record_contract, health_web3 = connect_with_contract(session['wallet_address'], HEALTH_RECORD_ARTIFACT_PATH)
        
        # Get the latest health data from the blockchain
        latest_data = health_record_contract.functions.getLatestHealthData(session['wallet_address']).call()
        
        # Get alerts from the notification system
        notification_contract, notification_web3 = connect_with_contract(session['wallet_address'], NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        alerts = notification_contract.functions.getUserAlerts(session['wallet_address']).call()
        
        # Process the latest data
        processed_data = {
            'heart_rate': latest_data[0],
            'spo2': latest_data[1],
            'temperature': latest_data[2],
            'systolic': latest_data[3],
            'diastolic': latest_data[4],
            'heart_rate_change': calculate_change(latest_data[0], 75),  # Assuming normal heart rate is 75
            'spo2_change': calculate_change(latest_data[1], 98),  # Assuming normal SpO2 is 98
            'temperature_change': calculate_change(latest_data[2], 37),  # Assuming normal temperature is 37
            'bp_change': calculate_change(latest_data[3], 120)  # Assuming normal systolic is 120
        }
        
        # Process alerts
        processed_alerts = []
        for alert in alerts:
            processed_alerts.append({
                'title': 'Health Alert',
                'message': alert[1],  # Alert message
                'timestamp': datetime.fromtimestamp(alert[2]).strftime('%Y-%m-%d %H:%M:%S')  # Convert timestamp to readable format
            })
        
        return render_template('dashboard.html', 
                             latest_data=processed_data,
                             alerts=processed_alerts)
                             
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        # Return default values if there's an error
        default_data = {
            'heart_rate': 0,
            'spo2': 0,
            'temperature': 0,
            'systolic': 0,
            'diastolic': 0,
            'heart_rate_change': 0,
            'spo2_change': 0,
            'temperature_change': 0,
            'bp_change': 0
        }
        return render_template('dashboard.html', 
                             latest_data=default_data,
                             alerts=[])

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

@app.route('/profile/settings', methods=['POST'])
@login_required
def update_settings():
    user_email = session['user_id']
    
    try:
        # Convert settings to integers (multiply by 100 for precision)
        settings = {
            'hr_high': int(float(request.form.get('hr_high'))),
            'hr_low': int(float(request.form.get('hr_low'))),
            'spo2_low': int(float(request.form.get('spo2_low'))),
            'temp_high': int(float(request.form.get('temp_high')) * 100),
            'temp_low': int(float(request.form.get('temp_low')) * 100)
        }
        
        # Update settings on blockchain
        tx = user_contract.functions.updateSettings(
            user_email,
            settings['hr_high'],
            settings['hr_low'],
            settings['spo2_low'],
            settings['temp_high'],
            settings['temp_low']
        ).buildTransaction({
            'from': user_web3.eth.default_account,
            'nonce': user_web3.eth.get_transaction_count(user_web3.eth.default_account)
        })
        
        # Sign and send transaction
        signed_tx = user_web3.eth.account.sign_transaction(tx, BLOCKCHAIN_PRIVATE_KEY)
        tx_hash = user_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
    except Exception as e:
        print(f"Settings update error: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    user_email = session['user_id']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        return redirect(url_for('profile'))
    
    try:
        # Hash passwords
        current_hash = user_web3.keccak(text=current_password).hex()
        new_hash = user_web3.keccak(text=new_password).hex()
        
        # Verify current password
        if user_contract.functions.verifyPassword(user_email, current_hash).call():
            # Update password on blockchain
            tx = user_contract.functions.changePassword(user_email, new_hash).buildTransaction({
                'from': user_web3.eth.default_account,
                'nonce': user_web3.eth.get_transaction_count(user_web3.eth.default_account),
                'gas': 2000000,
                'gasPrice': user_web3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = user_web3.eth.account.sign_transaction(tx, BLOCKCHAIN_PRIVATE_KEY)
            tx_hash = user_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
    except Exception as e:
        print(f"Password change error: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/notifications')
@login_required
def notifications():
    user_email = session['user_id']
    
    try:
        # Get notifications from blockchain
        messages, timestamps, read_status, types = notification_contract.functions.getNotifications(user_email).call()
        
        # Format notifications
        notifications = []
        for i in range(len(messages)):
            notifications.append({
                'message': messages[i],
                'timestamp': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': read_status[i],
                'type': types[i],
                'index': i
            })
        
        # Get unread count for badge
        unread_count = sum(1 for status in read_status if not status)
        
        return render_template('notifications.html', 
                             notifications=notifications,
                             unread_count=unread_count)
        
    except Exception as e:
        print(f"Notifications error: {str(e)}")
        return render_template('notifications.html', 
                             notifications=[],
                             unread_count=0)

@app.route('/notifications/mark-read/<int:index>', methods=['POST'])
@login_required
def mark_notification_read(index):
    user_email = session['user_id']
    
    try:
        # Mark notification as read on blockchain
        tx = notification_contract.functions.markNotificationAsRead(user_email, index).buildTransaction({
            'from': notification_web3.eth.default_account,
            'nonce': notification_web3.eth.get_transaction_count(notification_web3.eth.default_account),
            'gas': 2000000,
            'gasPrice': notification_web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = notification_web3.eth.account.sign_transaction(tx, BLOCKCHAIN_PRIVATE_KEY)
        tx_hash = notification_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = notification_web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Transaction failed'}), 500
            
    except Exception as e:
        print(f"Mark notification read error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/emergency-contacts')
@login_required
def emergency_contacts():
    user_email = session['user_id']
    wallet_address = session['wallet_address']
    
    try:
        # Create contract instance with user's wallet
        notification_contract_instance, _ = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        
        # Get emergency contacts from blockchain
        names, phones, emails = notification_contract_instance.functions.getEmergencyContacts(user_email).call()
        
        # Format contacts
        contacts = []
        for i in range(len(names)):
            contacts.append({
                'name': names[i],
                'phone': phones[i],
                'email': emails[i]
            })
        
        return render_template('emergency_contacts.html', contacts=contacts)
        
    except Exception as e:
        print(f"Emergency contacts error: {str(e)}")
        return render_template('emergency_contacts.html', error=f'Error loading contacts: {str(e)}')

@app.route('/emergency-contacts/add', methods=['POST'])
@login_required
def add_emergency_contact():
    user_email = session['user_id']
    wallet_address = session['wallet_address']
    name = request.form.get('name')
    phone = request.form.get('phone')
    contact_email = request.form.get('email')
    
    if not all([name, phone, contact_email]):
        return render_template('emergency_contacts.html', error='All fields are required')
    
    try:
        # Create contract instance with user's wallet
        notification_contract_instance, notification_web3_instance = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        
        # Add emergency contact on blockchain
        tx_hash = notification_contract_instance.functions.addEmergencyContact(
            user_email,
            name,
            phone,
            contact_email
        ).transact({
            'from': wallet_address,
            'gas': 2000000,
            'gasPrice': notification_web3_instance.eth.gas_price
        })
        
        # Wait for transaction receipt
        receipt = notification_web3_instance.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:  # Transaction successful
            return redirect(url_for('emergency_contacts'))
        else:
            return render_template('emergency_contacts.html', error='Failed to add emergency contact')
            
    except Exception as e:
        print(f"Add emergency contact error: {str(e)}")
        return render_template('emergency_contacts.html', error=f'Error adding contact: {str(e)}')

# Unused route - no UI implementation
# @app.route('/subscription/update', methods=['POST'])
# @login_required
# def update_subscription():
#     user_email = session['user_id']
#     status = request.form.get('status') == 'true'
    
#     try:
#         # Update subscription status on blockchain
#         tx = notification_contract.functions.updateSubscription(user_email, status).buildTransaction({
#             'from': notification_web3.eth.default_account,
#             'nonce': notification_web3.eth.get_transaction_count(notification_web3.eth.default_account),
#             'gas': 2000000,
#             'gasPrice': notification_web3.eth.gas_price
#         })
        
#         # Sign and send transaction
#         signed_tx = notification_web3.eth.account.sign_transaction(tx, 'YOUR_PRIVATE_KEY')
#         tx_hash = notification_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
#     except Exception as e:
#         print(f"Update subscription error: {str(e)}")
    
#     return jsonify({'status': 'success'})

@app.route('/api/health-data', methods=['GET'])
def receive_health_data():
    try:
        # Step 1: Initialize contracts properly
        health_contract, health_web3 = connect_with_contract(session.get('wallet_address', 0), HEALTH_RECORD_ARTIFACT_PATH)
        
        # Step 2: Fetch data from ThingSpeak
        thing_speak_url = "https://api.thingspeak.com/channels/2839570/status.json"
        response = requests.get(thing_speak_url)
        thing_speak_data = response.json()

        # Extract the latest data
        temperature = float(thing_speak_data['feeds'][-1]['field1'])
        heart_rate = int(thing_speak_data['feeds'][-1]['field2'])
        spo2 = int(thing_speak_data['feeds'][-1]['field3'])
        systolic = int(thing_speak_data['feeds'][-1]['field4'])
        diastolic = int(thing_speak_data['feeds'][-1]['field5'])
        
        # Get device_id and user_email from query params
        device_id = request.args.get('device_id', 'ESP32_001')  # Default device ID
        user_email = request.args.get('user_email', session.get('user_id', ''))  # Get from session if not in params

        # Convert temperature to integer (*100) for blockchain storage
        temp_int = int(temperature * 100)

        # Send transaction to blockchain
        tx = health_contract.functions.recordHealthData(
            device_id,
            temp_int,
            heart_rate,
            spo2
        ).buildTransaction({
            'from': health_web3.eth.default_account,
            'nonce': health_web3.eth.get_transaction_count(health_web3.eth.default_account),
            'gas': 2000000,
            'gasPrice': health_web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = health_web3.eth.account.sign_transaction(tx, BLOCKCHAIN_PRIVATE_KEY)
        tx_hash = health_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Check for health alerts
        check_health_alerts(user_email, {
            'heart_rate': heart_rate,
            'spo2': spo2,
            'temperature': temperature,
            'systolic': systolic,
            'diastolic': diastolic
        })

        return jsonify({
            "status": "success",
            "transaction_hash": health_web3.to_hex(tx_hash),
            "data": {
                "temperature": temperature,
                "heart_rate": heart_rate,
                "spo2": spo2,
                "systolic": systolic,
                "diastolic": diastolic
            }
        })

    except Exception as e:
        print(f"Error in health data endpoint: {str(e)}")  # Log the error
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/health-data/latest', methods=['GET'])
def get_latest_data():
    try:
        device_id = "ESP32_001"
        latest_data = health_contract.functions.getLatestData(device_id).call()
        
        return jsonify({
            "temperature": latest_data[1] / 100,  # Convert back from integer
            "heart_rate": latest_data[2],
            "spo2": latest_data[3],
            "timestamp": latest_data[0]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/alerts/<device_id>', methods=['GET'])
def get_device_alerts(device_id):
    try:
        alerts = health_contract.functions.getDeviceAlerts(device_id).call()
        return jsonify({
            "status": "success",
            "alerts": alerts
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def check_health_alerts(user_email, health_data):
    try:
        # Get user settings
        hr_high, hr_low, spo2_low, temp_high, temp_low = user_contract.functions.getUserSettings(user_email).call()
        
        # Check for alerts
        alerts = []
        
        if health_data['heart_rate'] > hr_high:
            alerts.append({
                'message': f'High heart rate alert: {health_data["heart_rate"]} bpm',
                'type': 'alert'
            })
        elif health_data['heart_rate'] < hr_low:
            alerts.append({
                'message': f'Low heart rate alert: {health_data["heart_rate"]} bpm',
                'type': 'alert'
            })
            
        if health_data['spo2'] < spo2_low:
            alerts.append({
                'message': f'Low SpO2 alert: {health_data["spo2"]}%',
                'type': 'alert'
            })
            
        if health_data['temperature'] > temp_high / 100:
            alerts.append({
                'message': f'High temperature alert: {health_data["temperature"]}°C',
                'type': 'alert'
            })
        elif health_data['temperature'] < temp_low / 100:
            alerts.append({
                'message': f'Low temperature alert: {health_data["temperature"]}°C',
                'type': 'alert'
            })
            
        # Check blood pressure alerts
        if health_data['systolic'] > 140:
            alerts.append({
                'message': f'High systolic pressure alert: {health_data["systolic"]} mmHg',
                'type': 'alert'
            })
        elif health_data['systolic'] < 90:
            alerts.append({
                'message': f'Low systolic pressure alert: {health_data["systolic"]} mmHg',
                'type': 'alert'
            })
            
        if health_data['diastolic'] > 90:
            alerts.append({
                'message': f'High diastolic pressure alert: {health_data["diastolic"]} mmHg',
                'type': 'alert'
            })
        elif health_data['diastolic'] < 60:
            alerts.append({
                'message': f'Low diastolic pressure alert: {health_data["diastolic"]} mmHg',
                'type': 'alert'
            })
        
        # Add alerts to blockchain
        for alert in alerts:
            tx = notification_contract.functions.addNotification(
                user_email,
                alert['message'],
                alert['type']
            ).buildTransaction({
                'from': notification_web3.eth.default_account,
                'nonce': notification_web3.eth.get_transaction_count(notification_web3.eth.default_account),
                'gas': 2000000,
                'gasPrice': notification_web3.eth.gas_price
            })
            
            signed_tx = notification_web3.eth.account.sign_transaction(tx, BLOCKCHAIN_PRIVATE_KEY)
            tx_hash = notification_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
    except Exception as e:
        print(f"Health alert check error: {str(e)}")

@app.route('/api/notifications/count')
@login_required
def get_notification_count():
    try:
        user_email = session['user_id']
        messages, timestamps, read_status, types = notification_contract.functions.getNotifications(user_email).call()
        
        # Count unread notifications
        unread_count = sum(1 for status in read_status if not status)
        
        return jsonify({
            'count': unread_count
        })
    except Exception as e:
        print(f"Error getting notification count: {str(e)}")
        return jsonify({
            'count': 0
        })

@app.route('/emergency-contacts/edit/<int:index>', methods=['POST'])
@login_required
def edit_emergency_contact(index):
    user_email = session['user_id']
    wallet_address = session['wallet_address']
    name = request.form.get('name')
    phone = request.form.get('phone')
    contact_email = request.form.get('email')
    
    if not all([name, phone, contact_email]):
        return render_template('emergency_contacts.html', error='All fields are required')
    
    try:
        # Create contract instance with user's wallet
        notification_contract_instance, notification_web3_instance = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        
        # Update emergency contact on blockchain
        tx_hash = notification_contract_instance.functions.updateEmergencyContact(
            user_email,
            index,
            name,
            phone,
            contact_email
        ).transact({
            'from': wallet_address,
            'gas': 2000000,
            'gasPrice': notification_web3_instance.eth.gas_price
        })
        
        # Wait for transaction receipt
        receipt = notification_web3_instance.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:  # Transaction successful
            return redirect(url_for('emergency_contacts'))
        else:
            return render_template('emergency_contacts.html', error='Failed to update emergency contact')
            
    except Exception as e:
        print(f"Edit emergency contact error: {str(e)}")
        return render_template('emergency_contacts.html', error=f'Error updating contact: {str(e)}')

@app.route('/emergency-contacts/delete/<int:index>', methods=['POST'])
@login_required
def delete_emergency_contact(index):
    user_email = session['user_id']
    wallet_address = session['wallet_address']
    
    try:
        # Create contract instance with user's wallet
        notification_contract_instance, notification_web3_instance = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
        
        # Delete emergency contact on blockchain
        tx_hash = notification_contract_instance.functions.deleteEmergencyContact(
            user_email,
            index
        ).transact({
            'from': wallet_address,
            'gas': 2000000,
            'gasPrice': notification_web3_instance.eth.gas_price
        })
        
        # Wait for transaction receipt
        receipt = notification_web3_instance.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:  # Transaction successful
            return redirect(url_for('emergency_contacts'))
        else:
            return render_template('emergency_contacts.html', error='Failed to delete emergency contact')
            
    except Exception as e:
        print(f"Delete emergency contact error: {str(e)}")
        return render_template('emergency_contacts.html', error=f'Error deleting contact: {str(e)}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 