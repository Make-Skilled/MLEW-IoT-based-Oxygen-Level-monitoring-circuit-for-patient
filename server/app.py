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
                
                # Hash the password - Make sure to use the same method as signup
                password_hash = Web3.keccak(text=password).hex()
                # Add '0x' prefix if not present
                if not password_hash.startswith('0x'):
                    password_hash = '0x' + password_hash
                
                # Get stored password hash
                stored_password = user_contract.functions.getUserPassword(email).call()
                
                # Debug prints
                print(f"Input password hash: {password_hash}")
                print(f"Stored password hash: {stored_password}")
                
                # Verify password using the contract's function
                is_valid = user_contract.functions.verifyPassword(email, Web3.toBytes(hexstr=password_hash)).call()
                
                if is_valid:
                    # Get additional user data
                    wallet_address = user_contract.functions.getUserWallet(email).call()
                    name = user_contract.functions.getUserName(email).call()
                    
                    # Set session data
                    session['user_id'] = email
                    session['wallet_address'] = wallet_address
                    session['user_name'] = name
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
            # Add '0x' prefix if not present
            if not password_hash.startswith('0x'):
                password_hash = '0x' + password_hash
            
            try:
                # Register user directly
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
            latest_data = health_record_contract.functions.getLatestData("ESP32_001").call()
            formatted_data = {
                "temperature": latest_data[1] / 100,  # Convert back from integer
                "heart_rate": latest_data[2],
                "spo2": latest_data[3],
                "timestamp": latest_data[0]
            }
        except Exception as data_error:
            print(f"Error getting health data: {str(data_error)}")
            formatted_data = {
                "temperature": None,
                "heart_rate": None,
                "spo2": None,
                "timestamp": None
            }
        
        # Get notifications/alerts
        try:
            notification_contract, notification_web3 = connect_with_contract(wallet_address, NOTIFICATION_SYSTEM_ARTIFACT_PATH)
            messages, timestamps, read_status, types = notification_contract.functions.getNotifications(session['user_id']).call()
            alerts = []
            for i in range(len(messages)):
                alerts.append({
                    'message': messages[i],
                    'timestamp': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M:%S'),
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
        # Provide default values when there's an error
        return render_template('dashboard.html', 
                             error=str(e),
                             latest_data={
                                 "temperature": None,
                                 "heart_rate": None,
                                 "spo2": None,
                                 "timestamp": None
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
def get_health_data():
    try:
        device_id = request.args.get('device_id', 'ESP32_001')
        
        # Update function name based on your contract
        data = health_contract.functions.getDeviceData(device_id).call()
        
        # Add null checks and proper indexing
        if not data or len(data) < 5:
            return jsonify({
                "status": "error",
                "message": "No data available"
            }), 404
            
        return jsonify({
            "status": "success",
            "data": {
                "temperature": data[0] / 100 if data[0] is not None else None,
                "heart_rate": data[1] if data[1] is not None else None,
                "spo2": data[2] if data[2] is not None else None,
                "systolic": data[3] if data[3] is not None else None,
                "diastolic": data[4] if data[4] is not None else None
            }
        })

    except Exception as e:
        print(f"Error in health data endpoint: {str(e)}")
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
        user_email = session.get('user_id')
        if not user_email:
            return jsonify({'count': 0})
            
        messages, timestamps, read_status, types = notification_contract.functions.getNotifications(user_email).call()
        
        # Add null check for read_status
        if not read_status:
            return jsonify({'count': 0})
            
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

@app.route('/debug/check-user/<email>')
def debug_check_user(email):
    try:
        user_data = user_contract.functions.getUserData(email).call()
        return jsonify({
            'exists': user_data[4],
            'name': user_data[0],
            'wallet': user_contract.functions.getUserWallet(email).call()
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 