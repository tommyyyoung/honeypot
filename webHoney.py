import logging
from flask import Flask, request, render_template
from logging.handlers import RotatingFileHandler

loggingFormat = logging.Formatter('%(asctime)s %(message)s')

hLogger = logging.getLogger('HTML Logger')
hLogger.setLevel(logging.INFO)
hHandler = RotatingFileHandler('audits.log', maxBytes = 2000, backupCount = 5)
hHandler.setFormatter(loggingFormat)
hLogger.addHandler(hHandler)

def webHoneypot(inputUsername = 'admin', inputPassword = 'password123'):
    app = Flask(__name__)
    
    @app.route('/')
    def landing():
        return render_template('landing.html')

    @app.route('/login')
    def login():
        return render_template('login.html')
    
    @app.route('/nebulusAdmin-login', methods = ['POST'])
    def adminLogin():
        username = request.form['username']
        password = request.form['password']

        ipAddr = request.remote_addr

        if username == inputUsername and password == inputPassword:
            hLogger.info(f"Successful login attempt from IP: {ipAddr}")
            return 'BOMBOCLAT YOU\'VE HACKED ME'
        else:
            hLogger.warning(f"Failed login attempt from IP: {ipAddr}")
            return 'Invalid credentials. Please try again.'
    
    return app

def runWebHoneypot(port = 8080, inputUsername = 'admin', inputPassword = 'password123'):
    runApp = webHoneypot(inputUsername, inputPassword)
    runApp.run(debug = False, port = port)